import math

def time_value(pv=None, fv=None, rate=None, periods=None):
    if rate is None and pv is not None and fv is not None and periods is not None:
        return (fv / pv) ** (1 / periods) - 1
    if pv is None and fv is not None and rate is not None and periods is not None:
        return fv / (1 + rate) ** periods
    if fv is None and pv is not None and rate is not None and periods is not None:
        return pv * (1 + rate) ** periods
    if periods is None and pv is not None and fv is not None and rate is not None:
        return math.log(fv / pv) / math.log(1 + rate)
    raise ValueError("Provide exactly three of: pv, fv, rate, periods")



print(time_value(fv=1000, rate=0.05, periods=3))       
print(time_value(pv=1000, rate=0.05, periods=3))      
print(time_value(pv=1000, fv=1157.63, rate=0.05))      
print(time_value(pv=1000, fv=1100, rate=None, periods=5))  







