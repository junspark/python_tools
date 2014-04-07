#!/usr/bin/env python

'''Nicely format a table, output in restructured text (reST) format'''

########### SVN repository information ###################
# $Date: 2013-05-22 15:29:45 -0500 (Wed, 22 May 2013) $
# $Author: jemian $
# $Revision: 1311 $
# $URL: https://subversion.xray.aps.anl.gov/bcdaext/APSpy/trunk/src/APSpy/rst_table.py $
# $Id: rst_table.py 1311 2013-05-22 20:29:45Z jemian $
########### SVN repository information ###################


import os, sys


class Table:
    '''
    Construct a table in reST (using no row or column spans)
    
    Each cell may have multiple lines, separated by a newline (\\n) character.
    
    For example, this code:
    
    ..  code-block:: python
        :linenos:
    
        from rst_table import Table
        t = Table()
        t.labels = ('Name', 'Type', 'Units', 'Description', )
        t.rows.append( ['uno', 'dos', 'tres', 'quatro', ] )
        t.rows.append( ['class', 'NX_FLOAT', '..', '..', ] )
        t.rows.append( ['1', '2', '3', '4', ] )
        print t.reST()
    
    generates this output:
    
    ..  code-block:: guess
        :linenos:
    
        ===== ======== ===== ===========
        Name  Type     Units Description
        ===== ======== ===== ===========
        uno   dos      tres  quatro     
        class NX_FLOAT ..    ..         
        1     2        3     4          
        ===== ======== ===== ===========
    
    which looks like this when formatted:

    ===== ======== ===== ===========
    Name  Type     Units Description
    ===== ======== ===== ===========
    uno   dos      tres  quatro     
    class NX_FLOAT ..    ..         
    1     2        3     4          
    ===== ======== ===== ===========


        
    .. rubric:: *class methods*

    '''
    
    def __init__(self):
        self.rows = []
        self.labels = []
        self.alignment = []
        self.longtable = False
     
    def reST(self, indentation = '', format = 'simple', **kws):
        '''return the table in reST format
        
        format may be one of these: *simple* (default), *complex*, or *list*
        '''
        if len(self.alignment) == 0:
            #  set the default column alignments
            self.alignment = ['L' for item in self.labels]
        if not len(self.labels) == len(self.alignment):
            raise "Number of column labels is different from column width specifiers"
        return {'default' : self.simple_table,
                'simple'  : self.simple_table,
                'complex' : self.complex_table,
                'list'    : self.list_table,}[format](indentation, kws)
      
    def simple_table(self, indentation = '', add_tabularcolumns=True):
        '''
        return the table in *simple* rest format

        ========== ========= ====== =================
        Name       Type      Units  Description      
        and                         (and Occurrences)
        Attributes                                   
        ========== ========= ====== =================
        one,       buckle my shoe.  ...              
        two                                        
        ..         ..        ..     ..
        ..         ..        ..     ..
        ..         ..        three, ..               
                             four                    
        uno        dos       tres   quatro           
        class      NX_FLOAT  ..     ..               
        1          2         3      4                
        ========== ========= ====== =================
        '''
        # maximum column widths, considering possible line breaks in each cell
        width = self.find_widths()
          
        # build the row separators
        separator = " ".join(['='*w for w in width]) + '\n'
        fmt = " ".join(["%%-%ds" % w for w in width]) + '\n'
          
        rest = indentation
        if add_tabularcolumns:
            rest += '.. tabularcolumns:: |%s|' % '|'.join(self.alignment)
        if self.longtable:
            rest += '\n%s%s' % (' '*4, ':longtable:')
        rest += '\n\n'
        rest += '%s%s' % (indentation, separator)        # top line of table
        rest += self._row(self.labels, fmt, indentation) # labels
        rest += '%s%s' % (indentation, separator)        # end of the labels
        for row in self.rows:
            rest += self._row(row, fmt, indentation)     # each row
        rest += '%s%s' % (indentation, separator)        # end of table
        return rest
      
    def complex_table(self, indentation = '', add_tabularcolumns=True):
        '''
        return the table in *complex* rest format
        
        +------------+-----------+--------+-------------------+
        | Name       | Type      | Units  | Description       |
        | and        |           |        | (and Occurrences) |
        | Attributes |           |        |                   |
        +============+===========+========+===================+
        | one,       | buckle my | shoe.  | ...               |
        | two        |           |        |                   |
        |            |           |        |                   |
        |            |           | three, |                   |
        |            |           | four   |                   |
        +------------+-----------+--------+-------------------+
        | uno        | dos       | tres   | quatro            |
        +------------+-----------+--------+-------------------+
        | class      | NX_FLOAT  | ..     | ..                |
        +------------+-----------+--------+-------------------+
        | 1          | 2         | 3      | 4                 |
        +------------+-----------+--------+-------------------+
        '''
        # maximum column widths, considering possible line breaks in each cell
        width = self.find_widths()
          
        # build the row separators
        separator = '+' + "".join(['-'*(w+2) + '+' for w in width]) + '\n'
        label_sep = '+' + "".join(['='*(w+2) + '+' for w in width]) + '\n'
        fmt = '|' + "".join([" %%-%ds |" % w for w in width]) + '\n'
          
        rest = indentation
        if add_tabularcolumns:
            rest += '.. tabularcolumns:: |%s|' % '|'.join(self.alignment)
        if self.longtable:
            rest += '\n%s%s' % (' '*4, ':longtable:')
        rest += '\n\n'
        rest += '%s%s' % (indentation, separator)        # top line of table
        rest += self._row(self.labels, fmt, indentation) # labels
        rest += '%s%s' % (indentation, label_sep)         # end of the labels
        for row in self.rows:
            rest += self._row(row, fmt, indentation)     # each row
            rest += '%s%s' % (indentation, separator)    # row separator
        return rest
      
    def list_table(self, indentation = '', add_tabularcolumns=True, title="Table"):
        '''
        return the table in *list-table* rest format (experimental)

        
        from: http://docutils.sourceforge.net/docs/ref/rst/directives.html
         
        .. list-table:: Table
            :header-rows: 3
        
            * - Name
              - Type
              - Units
              - Description
            * - and
              - 
              - 
              - (and Occurrences)
            * - Attributes
              - 
              - 
              - 
            * - one, two
              - buckle my
              - shoe. 
              
              
                three,
                four
              - ...
            * - uno
              - dos
              - tres
              - quatro
            * - class
              - NX_FLOAT
              - ..
              - ..
            * - 1
              - 2
              - 3
              - 4
        '''
        header_rows = max([len(item.splitlines()) for item in self.labels])
        subindent = ' '*4
        newline = '\n'
        row_start     = newline + indentation + subindent + '* - '
        item_start    = newline + indentation + subindent + '  - '
        continue_item = newline + indentation + subindent + ' '*4

        rest = indentation + ".. list-table:: " + title + newline
        rest += indentation + subindent + ":header-rows: " + str(header_rows) + newline
        
        for row in range(header_rows):
            for i, item in enumerate(self.labels):
                if i == 0:
                    rest += row_start
                else:
                    rest += item_start
                try:
                    value = item.splitlines()[row]
                except:
                    value = ''
                rest += value
        
        # TODO: get these multi-line items correct.  Each line in a separate table row
        for row in self.rows:
            for i, item in enumerate(row):
                if i == 0:
                    rest += row_start
                else:
                    rest += item_start
                rest += continue_item.join(item.splitlines())
        rest += newline

        return rest
   
   
    def _row(self, row, fmt, indentation = ''):
        '''
        Given a list of <entry nodes in this table <row, 
        build one line of the table with one text from each entry element.
        The lines are separated by line breaks.
        '''
        text = ""
        if len(row) > 0:
            for line_num in range( max(map(len, [str(_).split("\n") for _ in row])) ):
                item = [self._pick_line(str(r).split("\n"), line_num) for r in row]
                text += indentation + fmt % tuple(item)
        return text
      
    def find_widths(self):
        '''
        measure the maximum width of each column, 
        considering possible line breaks in each cell
        '''
        width = []
        if len(self.labels) > 0:
            width = [max(map(len, _.split("\n"))) for _ in self.labels]
        for row in self.rows:
            row_width = [max(map(len, str(_).split("\n"))) for _ in row]
            if len(width) == 0:
                width = row_width
            width = map( max, zip(width, row_width) )
        return width
      
    def _pick_line(self, text, lineNum):
        '''
        Pick the specific line of text or supply an empty string.
        Convenience routine when analyzing tables.
        '''
        if lineNum < len(text):
            s = text[lineNum]
        else:
            s = ""
        return s
 
 
if __name__ == '__main__':
    t = Table()
    t.labels = ('Name\nand\nAttributes', 'Type', 'Units', 'Description\n(and Occurrences)', )
    t.rows.append( ['one,\ntwo', "buckle my", "shoe.\n\n\nthree,\nfour", "..."] )
    t.rows.append( ['uno', 'dos', 'tres', 'quatro', ] )
    t.rows.append( ['class', 'NX_FLOAT', '..', '..', ] )
    t.rows.append( ['1', '2', '3', '4', ] )
    print t.reST()
    print '\n'*3
    t.alignment = ('l', 'L', 'l', 'L', )
    print t.reST(format='complex')
    print '\n'*3
    print t.reST(format='list')

    t = Table()
    t.labels = ('Name', 'Type', 'Units', 'Description', )
    t.rows.append( ['uno', 'dos', 'tres', 'quatro', ] )
    t.rows.append( ['class', 'NX_FLOAT', '..', '..', ] )
    t.rows.append( ['1', '2', '3', '4', ] )
    print t.reST()
