
'''simple support for cross-references'''


########### SVN repository information ###################
# $Date: 2013-04-24 18:41:03 -0500 (Wed, 24 Apr 2013) $
# $Author: jemian $
# $Revision: 1281 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/trunk/src/APSpy/cross_ref.py $
# $Id: cross_ref.py 1281 2013-04-24 23:41:03Z jemian $
########### SVN repository information ###################


class CrossReference(object):
    '''maintain a dictionary of cross-references'''
    
    def __init__(self, name = 'CrossReferenceList'):
        self.xref = {}
        if name == 'CrossReference':
            raise ValueError, 'class name already exists'
        self.name = name
    
    def add(self, key, value):
        '''add key = value to the cross-reference dictionary'''
        self.xref[key] = value
    
    def get(self, key):
        '''return the value of a specific key'''
        return self.xref[key]
    
    def get_keys(self):
        '''return the list of keys'''
        return self.xref.keys()
    
    def get_values(self):
        '''return the list of values'''
        return self.xref.values()
    
    def get_keys_dict(self):
        '''return the xref dict'''
        return self.xref
    
    def get_keys_enum(self):
        '''
        return a typesafe enum of the keys and values
        
        This is equivalent to defining a class named with the value of self.name.
        
        :see: http://docs.python.org/2/library/functions.html#type
        '''
        return type(self.name, (object, ), self.xref)


if __name__ == '__main__':
    xref = CrossReference('TestEnum')
    xref.add('meg', 1)
    xref.add('yergoo', 2)
    
    print xref.xref['meg']
    print xref.get('meg')
    
    keys = xref.get_keys_dict()
    print keys, keys['meg']
    
    keys = xref.get_keys_enum()
    print keys, keys.meg
