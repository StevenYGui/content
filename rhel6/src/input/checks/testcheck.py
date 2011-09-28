#!/usr/bin/python

import sys, os, tempfile, subprocess, platform
import idtranslate
import lxml.etree as ET

header = '''<?xml version="1.0" encoding="UTF-8"?>
<oval_definitions
	xmlns="http://oval.mitre.org/XMLSchema/oval-definitions-5"
    xmlns:unix="http://oval.mitre.org/XMLSchema/oval-definitions-5#unix"
    xmlns:ind="http://oval.mitre.org/XMLSchema/oval-definitions-5#independent"
    xmlns:linux="http://oval.mitre.org/XMLSchema/oval-definitions-5#linux"
    xmlns:oval="http://oval.mitre.org/XMLSchema/oval-common-5"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://oval.mitre.org/XMLSchema/oval-definitions-5#unix unix-definitions-schema.xsd
        http://oval.mitre.org/XMLSchema/oval-definitions-5#independent independent-definitions-schema.xsd
        http://oval.mitre.org/XMLSchema/oval-definitions-5#linux linux-definitions-schema.xsd
        http://oval.mitre.org/XMLSchema/oval-definitions-5 oval-definitions-schema.xsd
        http://oval.mitre.org/XMLSchema/oval-common-5 oval-common-schema.xsd">
       <generator>
        <oval:product_name>testcheck.py</oval:product_name>
        <oval:product_version>0.0.1</oval:product_version>
        <oval:schema_version>5.10</oval:schema_version>
        <oval:timestamp>2011-09-23T13:44:00</oval:timestamp>
    </generator>'''
footer = '</oval_definitions>'

ovalns = "http://oval.mitre.org/XMLSchema/oval-definitions-5"

# globals, to make recursion easier in case we encounter extend_definition
definitions = ET.Element("definitions")
tests = ET.Element("tests")
objects = ET.Element("objects")
states = ET.Element("states")
variables = ET.Element("variables")

# add oval elements to the global Elements defined above
def add_oval_elements(body):
    tree = ET.fromstring(header + body + footer)
    # parse new file(string) as an etree, so we can arrange elements appropriately 
    for childnode in tree.findall("./{" + ovalns + "}def-group/*"):
        print "tag: " + childnode.tag
        if childnode.tag == ("{" + ovalns + "}definition"):
            definitions.append(childnode)
            defname = childnode.get("id")
            #for testchild in childnode.getchildren():
            #    print "testchild is " + testchild.tag
            for defchild in childnode.findall(".//{" + ovalns + "}extend_definition"):
                defid = defchild.get("definition_ref")            
                print "got extended defid " + defid
                includedbody = read_ovaldefgroup_file(defid+".xml")
                add_oval_elements(includedbody)
        if childnode.tag.endswith("_test"): tests.append(childnode)
        if childnode.tag.endswith("_object"): objects.append(childnode)
        if childnode.tag.endswith("_state"): states.append(childnode)
        if childnode.tag.endswith("_variable"): variables.append(childnode)
    return defname

def read_ovaldefgroup_file(testfile):
    with open( testfile, 'r') as f:
        body = f.read()
    return body

def main():
    if len(sys.argv) < 2:
        print "Provide the name of an XML file, which contains the definition (and dependencies) to test."
        sys.exit(1)

    for testfile in sys.argv[1:]:
        body = read_ovaldefgroup_file(testfile)
        defname = add_oval_elements(body)
        ovaltree = ET.fromstring(header + footer)
        # append each major element type, if it has subelements
        for element in [definitions, tests, objects, states, variables]:
            if element.getchildren():
                ovaltree.append(element)
        # re-map all the element ids from meaningful names to meaningless numbers
        testtranslator = idtranslate.idtranslator("testing.ini", "oval:scap-security-guide.testing")
        ovaltree = testtranslator.translate(ovaltree)
        (ovalfile, fname) = tempfile.mkstemp(prefix=defname,suffix=".xml")
        os.write(ovalfile, ET.tostring(ovaltree))
        os.close(ovalfile)
        print "fname is " + fname
        subprocess.call("ls -l " + fname, shell=True)
		# temporary workaround for fedora/redhat oscap version differences
        (distname, distversion, distcodename) = platform.linux_distribution(full_distribution_name=0)
        if distname == 'redhat':
            subprocess.call("/usr/bin/oscap oval eval --result-file "+ fname + "-results " + fname, shell=True)
        else:
            subprocess.call("/usr/bin/oscap oval eval --results "+ fname + "-results " + fname, shell=True)
        # perhaps delete tempfile?

    sys.exit(0)

if __name__ == "__main__":
    main()

