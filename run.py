from main import MintChain_Bot,logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time
from apscheduler.triggers.cron import CronTrigger
bot=MintChain_Bot()

def task():
    try:
        wallet=bot.wallets[0]
        bot.login(wallet=wallet)
        bot.get_energy_list(wallet=wallet)
        bot.claim_energy(wallet=wallet)
        bot.inject_energy(wallet=wallet)
    except:
        pass
# 创建调度器
scheduler = BackgroundScheduler()

# 定义一个每24小时执行一次的触发器
trigger = CronTrigger(hour=0, minute=30)

# 添加任务到调度器
scheduler.add_job(task, trigger)
task()
# 启动调度器
scheduler.start()

# 让主线程保持运行，以便调度器可以执行任务
try:
    while True:
        time.sleep(1)
except Exception as e:
    logger.error(f"{e}")
    # 关闭调度器
    scheduler.shutdown()