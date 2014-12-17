import sys
import re
import time
import datetime

def parse_file(inputfile, outputfile):
    beginning = False
    pre = re.compile('.*netassay.evaluation: CRITICAL SETUP COMPLETE')
    beg = re.compile('(.+?) netassay.evaluation: CRITICAL BEGIN UPDATE')
    mid1 = re.compile('(.+?) netassay.evaluation: CRITICAL _RULE_TIMER ([0-9]+)')
    mid2 = re.compile('(.+?) netassay.evaluation: CRITICAL _UPDATE_RULES')
    dly = re.compile('(.+?) netassay.evaluation: CRITICAL INSERT DELAY')
    fin = re.compile('(.+?) netassay.evaluation: CRITICAL FINISHED UPDATE')
    norules  = re.compile('(.+?) netassay.evaluation: CRITICAL NO RULES TO ADD')
    addrules = re.compile('(.+?) netassay.evaluation: CRITICAL RULES TO ADD')
    class_size = re.compile('(.+?) netassay.evaluation: CRITICAL CLASSIFIER LEN = ([0-9]+)')

    begtime  = []
    midtime  = []
    midcount = []
    fintime  = None
    size     = 0
    
    norulescount  = 0
    addrulescount = 0
    


    
    lncount = 1 #count starts at line 1 (there is no line 0).
    for line in inputfile:
        # get past the setup stage
        if beginning == False:
            if pre.match(line) != None:
                print "At the beginning."
                beginning = True
        else:
            if addrules.match(line) != None:
                addrulescount = addrulescount + 1
                # easy case, nothing more to do

            elif norules.match(line) != None:
                norulescount = norulescount + 1
                # Need to complete the one that's associated with the
                # no-rules-to-add condition
#FIXME
                norulestime = parse_date(norules.match(line).groups()[0])
                for i in range(0, midcount[0]):
                    entry = begtime[i]
                    output_string = str(entry) + ", "
                    delta = midtime[0] - entry
                    output_string = output_string + str(delta) + ", "
                    delta = norulestime - entry
                    output_string = output_string + str(delta) + ", "
                    output_string = output_string + size + ", "
                    output_string = output_string + str(addrulescount) + ", "
                    output_string = output_string + str(norulescount) + "\n"

                begtime = begtime[midcount[0]:]
                midtime = midtime[1:]
                midcount = midcount[1:]

            elif beg.match(line) != None:
                begtime.append(parse_date(beg.match(line).groups()[0]))
                
            elif mid1.match(line) != None:
                #specifies the number of rules this applies to.
                midtime.append(parse_date(mid1.match(line).groups()[0]))
                midcount.append(int(mid1.match(line).groups()[1]))

            elif mid2.match(line) != None:
                #does not specify number of rules, always is 1.
                midtime.append(parse_date(mid2.match(line).groups()[0]))
                midcount.append(1)

# IGNORING FOR NOW.
#            elif dly.match(line) != None:
                #mid and dly are, effectively, the same
#                midtime.append(parse_date(dly.match(line).groups()[0]))
#                pass

            elif class_size.match(line) != None:
                #don't care about timestamp here. 
                size = class_size.match(line).groups()[1]

            elif fin.match(line) != None:
                # Write out everything
                fintime = parse_date(fin.match(line).groups()[0])
                
                for i in range(0, midcount[0]):
                    entry = begtime[i]
                    output_string = str(entry) + ", "
                    delta = midtime[0] - entry
                    output_string = output_string + str(delta) + ", "
                    delta = fintime - entry
                    output_string = output_string + str(delta) + ", "
                    output_string = output_string + size + ", "
                    output_string = output_string + str(addrulescount) + ", "
                    output_string = output_string + str(norulescount) + "\n"

                begtime = begtime[midcount[0]:]
                midtime = midtime[1:]
                midcount = midcount[1:]

                
        if (lncount % 1000 == 0):
            print "On line " + str(lncount)
        lncount = lncount + 1

    print "Beg has : " + str(len(begtime))
    print "Mid has : " + str(len(midtime))

def parse_date(datestring):
    return datetime.datetime.strptime(datestring, "%Y-%m-%d %H:%M:%S,%f")
            
            
        
        


if __name__ == "__main__":

    inputfile = open('/home/mininet/netassay-optimization/netassay.log', 'r')
    outfilename = time.strftime("/home/mininet/netassay-optimization/pyretic/modules/netassay/eval/output/%Y%m%d-%H%M%S-parsed.csv")
    outputfile = open(outfilename, 'w+')

    parse_file(inputfile,outputfile)
    inputfile.close()
    outputfile.close()
               
