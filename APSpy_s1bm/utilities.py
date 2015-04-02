def PreampUnitConversion(s, u):
    # s     : sensitivity setting number
    # u     : unit setting number
    
    s = PreampS(s);
    u = PreampU(u);
    s_in_nA = s*u;
    
    return s_in_nA
    
def PreampS(s):
    return {
        '0': 1,
        '1': 2,
        '2': 5,
        '3': 10,
        '4': 20,
        '5': 50,
        '6': 100,
        '7': 200,
        '8': 500,
        }.get(s, 9) # 9 is default if x not found
        
def PreampU(u):
    return {
        '0': 0.001,
        '1': 1,
        '2': 1000,
        '3': 1000000,
        }.get(u, 9) # 9 is default if x not found
