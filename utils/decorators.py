from datetime import datetime,timedelta
from functools import wraps
import time
# from rest_framework.response import Response
from fastapi.responses import Response,JSONResponse


def performanceLogger(printArgs=False,generateLog=False, logFilename='performance_log.txt'):
    def formatElapsedTime(elapsed_time):
        if elapsed_time < 1e-6:  # Check if elapsed time is very small (less than 1 microsecond)
            return f"{elapsed_time * 1e6:.2f} microseconds"
        elif elapsed_time < 1e-3:  # Check if elapsed time is less than 1 millisecond
            return f"{elapsed_time * 1e3:.2f} milliseconds"
        elif elapsed_time < 1:
            return f"{elapsed_time:.2f} seconds"
        elif elapsed_time < 60:
            return f"{elapsed_time:.2f} seconds"
        elif elapsed_time < 3600:
            return f"{elapsed_time / 60:.2f} minutes"
        else:
            return f"{elapsed_time / 3600:.2f} hours"
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            formatted_time = formatElapsedTime(elapsed_time)
            
            if printArgs:
                logMsg = f"Function: {func.__name__}, Time: {formatted_time}, Arguments: {args}, {kwargs}"
            else:
                logMsg = f"Function: {func.__name__}, Time: {formatted_time}"
            if generateLog:
                with open(logFilename, 'a') as log_file:
                    log_file.write(logMsg + '\n')
            print(logMsg) 

            return result

        return wrapper
    return decorator

def exceptionHandler(returnVal=None, errorPrint=True,msg=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                if returnVal is not None and 'api' in returnVal:
                    try:
                        return result
                    except Exception as e:
                        return JSONResponse({"error": True,"data": None,"msg": "SOMETHING_WENT_WRONG","sysError":str(e)})
                else:
                    return result
            except Exception as e:
                if errorPrint:
                    print(f"SOMETHING WENT WRONG IN {func.__name__}: {str(e)}")
                if returnVal is None:
                    return returnVal
                elif 'api' in returnVal:
                    return JSONResponse({"error": True,"data": None,"msg": "SOMETHING_WENT_WRONG","sysError":str(e)})
                else:
                    return returnVal
        return wrapper
    return decorator

def apply_decorators(decorators):
    def decorator(func):
        for dec in reversed(decorators):
            func = dec(func)
        return func
    return decorator
 