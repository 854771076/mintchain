from web3 import Web3
from loguru import logger
import json,os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from  fake_useragent import UserAgent
from eth_account.messages import encode_defunct
import requests
from datetime import timedelta,datetime
import time
import threading
from functools import *
logger.add(
    "MintChain_Bot.log",
    rotation="1 week",
    retention="1 month",
    level="INFO",
    format="{time} {level} {message}",
    compression="zip"  # 轮换日志文件时进行压缩
)

def log(msg):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            wallet = kwargs.get('wallet')  # 使用默认值处理没有 wallet 的情况
            if wallet:
                name = wallet.get('name')  # 从 wallet 中获取 name
                try:
                    func(*args, **kwargs)
                    logger.success(f'{name}-{msg}成功')
                except Exception as e:
                    logger.error(f'{name}-{msg}失败: {e}')
            else:
                try:
                    func(*args, **kwargs)
                    logger.success(f'{msg}成功')
                except Exception as e:
                    logger.error(f'{msg}失败: {e}')
        return wrapper
    return decorator

ua=UserAgent()
class MintChain_Bot:
    headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Authorization': 'Bearer',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            # Already added when you pass json=
            # 'Content-Type': 'application/json',
            # Requests sorts cookies= alphabetically
            'Cookie': '_ga=GA1.1.863294364.1716792164; wagmi.metaMask.disconnected=true; wagmi.recentConnectorId="io.metamask"; _ga_GEWYCVR3FT=GS1.1.1723189730.19.0.1723189730.0.0.0; wagmi.store={"state":{"connections":{"__type":"Map","value":[["785a1f8b178",{"accounts":["0x72691a36ED1fAC3b197Fb42612Dc15a8958bf9f2"],"chainId":185,"connector":{"id":"io.metamask","name":"MetaMask","type":"injected","uid":"785a1f8b178"}}]]},"chainId":185,"current":"785a1f8b178"},"version":2}',
            'Origin': 'https://www.mintchain.io',
            'Pragma': 'no-cache',
            'Referer': 'https://www.mintchain.io/mint-forest',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': ua.chrome,
            'sec-ch-ua': '"Not)A;Brand";v="99", "Microsoft Edge";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
    _lock=threading.Lock()
    def __init__(self,invited='RRU30',wallet_path='./wallets',proxy_api='http://zltiqu.pyhttp.taolop.com/getip?count=10&neek=42670&type=2&yys=0&port=2&sb=&mr=1&sep=0&ts=1',rpc_url = 'https://rpc.mintchain.io'):
        '''
        invited 邀请码
        wallet_path 钱包存放目录
        proxy_api 代理接口
        rpc_url RPC接口
        '''
        self.proxy_api=proxy_api
        self.rpc_url=rpc_url
        self.wallet_path=wallet_path
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.invited=invited
        self.ip_pool=[]
        
        # 检查连接是否成功
        if not self.web3.is_connected():
            raise Exception("无法连接到 plumenet 节点")
        
        self.chain_id=185
        # 初始化钱包
        self.wallets=[]
        self.get_wallets()
    def load_wallet(self,filename):
        '''
        加载钱包
        '''
        # 从 JSON 文件中读取钱包信息
        with open(filename, 'r') as file:
            wallet_info = json.load(file)
        wallet_name=filename.split('/')[-1].replace('.json','')
        wallet_info['name']=wallet_name
        wallet_info['filename']=filename
        
        return wallet_info
    def create_wallets(self,num=1):
        '''
        批量创建钱包
        '''
        index=len(self.wallets)+1
        for i in range(index,index+num):
            filename=os.path.join(self.wallet_path,f'wallet{i}.json')
            self.generate_and_save_wallet(filename)
            wallet=self.load_wallet(filename)
            self.wallets.append(
            wallet
            )
    @log('加载钱包')
    def get_wallets(self,max_workers=10):
        '''
        获取钱包保存目录下所有钱包
        '''
        self.wallets=[]
        wallets_list = glob.glob(os.path.join(self.wallet_path, '*'))
        # 使用线程池来并发加载钱包
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.load_wallet, wallet) for wallet in wallets_list]

            for future in as_completed(futures):
                try:
                    wallet_data = future.result()
                    self.wallets.append(wallet_data)
                except Exception as e:
                    logger.error(f"Error loading wallet: {e}")
        return wallets_list
    def get_sign(self,wallet,msg):
        '''
        钱包签名
        '''
        # 账户信息
        private_key = wallet['private_key']
        address =wallet['address']
        # 使用web3.py编码消息
        message_encoded = encode_defunct(text=msg)
        # 签名消息
        signed_message = self.web3.eth.account.sign_message(message_encoded, private_key=private_key)
        # 打印签名的消息
        return signed_message.signature.hex()
    @log('登录')
    def login(self,wallet):
        address=wallet['address']
        msg=f'You are participating in the Mint Forest event: \n {address}\n\nNonce: 6210396'
        json_data = {
            'address':address ,
            'signature': self.get_sign(wallet=wallet,msg=msg),
            'message': msg,
        }
        response = requests.post('https://www.mintchain.io/api/tree/login', headers=self.headers, json=json_data)
        data=response.json()['result']
        wallet['access_token']=data['access_token']
        wallet['user']=data['user']
    def get_headers(self,wallet):
        headers=self.headers.copy()
        headers['Authorization']='Bearer '+wallet['access_token']
        return headers
    @log('获取能量列表')  
    def get_energy_list(self,wallet):
        response = requests.get('https://www.mintchain.io/api/tree/energy-list', headers=self.get_headers(wallet))
        wallet['energy_list']=response.json()['result']
        return wallet['energy_list']
    def get_energy_balance(self,wallet):
        response = requests.get('https://www.mintchain.io/api/tree/user-info',headers=self.get_headers(wallet))
        data=response.json()
        wallet['energy']=int(data['result']['energy'])
        return wallet['energy']
    def claim_energy(self,wallet):
        for energy in wallet['energy_list']:
            json_data = {
                **energy,'id':f'_{energy["amount"]}'
            }
            response = requests.post('https://www.mintchain.io/api/tree/claim',  headers=self.get_headers(wallet), json=json_data)
            data=response.json()
            if data['msg']=='ok':
                
                energy=self.get_energy_balance(wallet=wallet)
                logger.success(f'领取能量成功：{data["result"]},余额：{energy}')
            else:
                logger.error(f'领取能量失败：{data}')
    def inject_energy(self,wallet):
        energy=self.get_energy_balance(wallet=wallet)
        json_data = {
            'energy': energy,
            'address': wallet['address'],
        }
        response = requests.post('https://www.mintchain.io/api/tree/inject',headers=self.get_headers(wallet), json=json_data)
        data=response.json()
        if data['msg']=='ok':
            energy=self.get_energy_balance(wallet=wallet)
            logger.success(f'注入能量成功：{data["result"]},余额：{energy}')
        else:
            logger.error(f'注入能量失败：{data}')
if __name__=='__main__':
    bot=MintChain_Bot()
    wallet=bot.wallets[0]
    bot.login(wallet=wallet)
    bot.get_energy_list(wallet=wallet)
    bot.claim_energy(wallet=wallet)
    bot.inject_energy(wallet=wallet)
    print(bot)