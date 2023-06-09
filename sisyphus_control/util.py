import inspect

def ensure_coroutine(listener):
    if inspect.iscoroutinefunction(listener):
        return listener
    else:

        async def async_listener(*args):
            listener(*args)

        return async_listener