import asyncio
from queue import Queue
from threading import Thread

import nest_asyncio
nest_asyncio.apply()    # 主要解决循环体的嵌套事件, 没有这个语句会报错: This event loop is already running

from sys import version_info

class async_do():
    def __init__(self, sema = 100):                     # 构造函数, 类实例化的时候被调用
        self.sema = asyncio.Semaphore(sema)             # 设置信号量
        self.taskQu = Queue()
        if version_info.major >= 3 and version_info.minor >= 9:
            self.loop = asyncio.new_event_loop()        # 高版本用这两句的不会出现get_event_loop中警告 DeprecationWarning: There is no current event loop
            asyncio.set_event_loop(self.loop)           # 建议3.9以前使用get_event_loop(), 3.9以及之后
        else:
            self.loop = asyncio.get_event_loop()        # get_event_loop 获取循环体兼容性较好, 但是高版本会有一个警告
        
        
    def __call__(self, proc, callback, *args, **kwds):  # 调用函数, 类的实例化可以直接当函数用, 用的时候执行这个过程
        self.add(proc, callback, *args, **kwds)
        
    def add(self, proc, callback, *args, **kwds):               # 增加任务
        t = self.loop.create_task(proc(self.sema, *args, **kwds))
        if callback: t.add_done_callback(callback)
        self.taskQu.put(t)
        
    def submit(self, proc, callback, *args, **kwds):            # 提交任务, 等同于增加任务
        self.add(proc, callback, *args, **kwds)
        
    def map(self, proc, callback, arg_list: list = None):       # 映射任务
        '''arg_list 可以是元组组成的列表, 也可以是字典列表'''
        if arg_list is None: return 
        in_type_list = lambda data, type_list: any(isinstance(data, t) for t in type_list)

        for arg in arg_list:
            if in_type_list(arg, [list, tuple, set]): self.add(proc, callback, *arg)
            elif in_type_list(arg, [dict]): self.add(proc, callback, **arg)
            else: self.add(proc, callback, arg)

    def _go(self, func, *args, **kwds):                         # 多线程调用
        mthread=Thread(target=func, args=args, kwargs=kwds)
        mthread.daemon = kwds.pop('nowait', False)
        mthread.start()
    
    
    def wait(self):                                             # 等待任务队列执行完
        if t := [self.taskQu.get_nowait() for _ in range(self.taskQu.qsize())]:
            self.loop.run_until_complete(asyncio.wait(t))


    def no_wait(self):                                          # 不等待任务队列执行
        self._go(self.wait)
        

async def some_job(sema, x):                                    # 协程任务, 注意必须以信号量sema作为第一个参数, 因为代码25行用self.sema作为第一个参数了
    async with sema:
        await asyncio.sleep(0.5)
        print(x)
        return x   
def deal_result(r):                                             # 结果处理
    print(r.result())
        
ado = async_do(20)  # 通过信号量控制协程数量

# 基础用法
for i in range(100):
    ado.add(some_job, None, i)  # submit等价于add
ado.wait()

# 不等待用法
for i in range(100,200):
    ado.add(some_job, None, i)
ado.no_wait()                   # 创建一个线程来执行

# map映射参数列表用法
tasks = list(range(200, 300))
ado.map(some_job, deal_result, tasks)   # 映射一个任务列表
ado.wait()
