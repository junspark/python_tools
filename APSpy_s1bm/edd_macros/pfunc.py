def pkGaussian(x, *p):
    # c0    : constant 4*log(2)
    # A     : intensity
    # x     : (tth-tth_peak)/Gamma
    # Gamma : FWHM
    c0 = 4*numpy.log(2)
    A, Gamma, xPeak, n0, n1 = p
    
    delx = (x - xPeak)/Gamma
    
    ybkg = numpy.polyval([n0, n1], x)
    yG = A*(c0**0.5/Gamma/numpy.pi**0.5)*numpy.exp(-c0*delx**2)
    ypk = ybkg + yG
    
    return ypk
