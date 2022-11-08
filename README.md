# async_class
Python协程类, 用来简化协程代码编写

协程代码编写过程中, 往往因为各种报错而懊恼, 本项目主要为了让协程写的跟多线程一样简单

因为类比较简单, 就直接写在readme中了.

环境 Python3, 需要安装nest_asyncio, 其他应该是默认库

```
import asyncio
from queue import Queue
from threading import Thread

import nest_asyncio
nest_asyncio.apply()    # 主要解决循环体的嵌套事件, 没有这个语句会报错: This event loop is already running

class async_do():
    def __init__(self, sema = 100):                   # 构造函数, 类实例化的时候被调用
        self.sema = asyncio.Semaphore(sema)
        self.taskQu = Queue()
        # self.loop = asyncio.get_event_loop()          # 此处用new_event_loop会导致两个协程循环体而跟Semaphore产生报错, 等价于下面两句, 但是会有一个警告
        self.loop = asyncio.new_event_loop()            # 这两句的作用是不会出现get_event_loop中警告 DeprecationWarning: There is no current event loop
        asyncio.set_event_loop(self.loop)
        
    def __call__(self, proc, callback, *args, **kwds):      # 调用函数, 类的实例化可以直接当函数用, 用的时候执行这个过程
        self.add(proc, callback, *args, **kwds)
        
    def add(self, proc, callback, *args, **kwds):
        t = self.loop.create_task(proc(self.sema, *args, **kwds))
        if callback: t.add_done_callback(callback)
        self.taskQu.put(t)
        
    def submit(self, proc, callback, *args, **kwds):
        self.add(proc, callback, *args, **kwds)
        
    def map(self, proc, callback, arg_list: list = None):
        '''arg_list 可以是元组组成的列表, 也可以是字典列表'''
        if arg_list is None: return 
        in_type_list = lambda data, type_list: any(isinstance(data, t) for t in type_list)

        for arg in arg_list:
            if in_type_list(arg, [list, tuple, set]): self.add(proc, callback, *arg)
            elif in_type_list(arg, [dict]): self.add(proc, callback, **arg)
            else: self.add(proc, callback, arg)

    def _go(self, func, *args, **kwds):
        mthread=Thread(target=func, args=args, kwargs=kwds)
        mthread.daemon = kwds.pop('nowait', False)
        mthread.start()
    
    
    def wait(self):
        if t := [self.taskQu.get_nowait() for _ in range(self.taskQu.qsize())]:
            self.loop.run_until_complete(asyncio.wait(t))


    def no_wait(self):
        self._go(self.wait)
        

async def some_job(sema, x):
    async with sema:
        await asyncio.sleep(0.5)
        print(x)
        return x   
def deal_result(r):
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
```

执行效果就是协程执行300次打印, 非常完美

![image](https://user-images.githubusercontent.com/17432059/200625907-ff664b53-4a26-4788-bed5-d2a3ad78bf59.png)




