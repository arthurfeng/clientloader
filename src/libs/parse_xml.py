# -*- coding: utf-8 -*-

from xml.dom import minidom

class XML():

    '''
    This Class Is used to parse xml file
    '''

    def __init__(self):

	pass

    def get_attrvalue(self,node,attrname):
        if node:
            return node.getAttribute(attrname)
        else:
	    return 0

    def set_attrvalue(self, node, key, value):

	if node:
	    return node.setAttribute(key, value)
        else:
	    ''

    def get_nodevalue(self,node, index = 0):
        length = len(node.childNodes)
        if node and length != 0:
            return node.childNodes[index].nodeValue
        else:
            return 0

    def get_xmlnode(self,node,name):
        if node:
            return node.getElementsByTagName(name)
        else:
            return []

    def xml_to_string(self,filename):
        doc = minidom.parseString(filename)
        return doc.toxml('UTF-8')

    def string_to_xml(self, filename):

	doc = minidom.parseString(filename)
	return doc.documentElement

def main():
    import sys
    f = open(sys.argv[1],'r')
    lines = f.read()
    f.close()
    P =XML()
    result, message, a, b = P.start(lines)
    print  a
    print b

if __name__ == '__main__':

    main()
