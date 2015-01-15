import sys
import re
import time
import datetime

def parse_file(inputfile, outputfile):

    #All the regexes
    pre = re.compile('(.+?) netassay.evaluation: CRITICAL SETUP COMPLETE')
    install_rule = re.compile('(.+?) netassay.evaluation2: CRITICAL INSTALL_RULE ([0-9]+)')
    uninstall_rule = re.compile('(.+?) netassay.evaluation2: CRITICAL UNINSTALL_RULE ([0-9]+)')
    add_rule = re.compile('(.+?) netassay.evaluation2: CRITICAL ADD_RULE ([0-9]+)')
    remove_rule = re.compile('(.+?) netassay.evaluation2: CRITICAL REMOVE_RULE ([0-9]+)')
    no_delay = re.compile('(.+?) netassay.evaluation2: CRITICAL NO_DELAY ([0-9]+)')
    with_delay = re.compile('(.+?) netassay.evaluation2: CRITICAL WITH_DELAY ([0-9]+)')
    rules_to_add = re.compile('(.+?) netassay.evaluation2: CRITICAL RULES_TO_ADD')
    no_rules_to_add = re.compile('(.+?) netassay.evaluation2: CRITICAL NO_RULES_TO_ADD')
    update_rules = re.compile('(.+?) netassay.evaluation2: CRITICAL UPDATE_RULES')
    update_rules_finished = re.compile('(.+?) netassay.evaluation2: CRITICAL UPDATE_RULES_FINISHED')

    outstanding = {}
    updating = {}
    
    beginning = False


    lncount = 1
    for line in inputfile:
        # get past the setup stage
        if beginning == False:
            if pre.match(line) != None:
                print "At the beginning. Line: " + str(lncount)
                beginning = True
                beginning_time = parse_date(pre.match(line).groups()[0])
        else:

            # Start of a rule change
            if add_rule.match(line) != None:
                date = parse_date(add_rule.match(line).groups()[0])
                serial = add_rule.match(line).groups()[1]
                outstanding[serial] = {'add-remove-time': date, 'type':"add"}

            elif remove_rule.match(line) != None:
                date = parse_date(remove_rule.match(line).groups()[0])
                serial = remove_rule.match(line).groups()[1]
                outstanding[serial] = {'add-remove-time': date, 'type':"remove"}

            elif install_rule.match(line) != None:
                date = parse_date(install_rule.match(line).groups()[0])
                serial = install_rule.match(line).groups()[1]
                if (serial not in outstanding.keys()):
                    outstanding[serial] = {'add-remove-time': beginning_time, 
                                           'type':"add", 'delay':True}
                outstanding[serial]['install-time'] = date

            elif uninstall_rule.match(line) != None:
                date = parse_date(uninstall_rule.match(line).groups()[0])
                serial = uninstall_rule.match(line).groups()[1]
                if (serial not in outstanding.keys()):
                    outstanding[serial] = {'add-remove-time': beginning_time, 
                                           'type':"remove", 'delay':True}
                outstanding[serial]['install-time'] = date

            elif no_delay.match(line) != None:
                serial = no_delay.match(line).groups()[1]
                outstanding[serial]['delay'] = False

            elif with_delay.match(line) != None:
                serial = with_delay.match(line).groups()[1]
                outstanding[serial]['delay'] = True


            elif update_rules_finished.match(line) != None:
                date = parse_date(update_rules_finished.match(line).groups()[0])
                for key in updating.keys():
                    updating[key]['update-finish'] = date

                    serial = key
                    total_time = updating[key]['update-finish'] - updating[key]['add-remove-time']
                    optimization_time = (updating[key]['update-finish'] -
                                         updating[key]['update-start'])
                    delay = updating[key]['delay']
                    if delay == False:
                        delay_time = datetime.timedelta() #init to 0
                    else:
                        delay_time = (updating[key]['install-time'] -
                                      updating[key]['add-remove-time'])
                    
                    
                    entry = str(serial) + ", " 
                    entry = entry + str(total_time) + ", "
                    entry = entry + str(delay) + ", "
                    entry = entry + str(delay_time) + ", "
                    entry = entry + str(optimization_time) + "\n"
                    outputfile.write(entry)
                updating = {}

            # This comes after update_rules_finished as it, too,
            # matches on UPDATE_RULES_FINISHED.
            elif update_rules.match(line) != None:
                date = parse_date(update_rules.match(line).groups()[0])
                for key in outstanding.keys():
                    if 'install-time' in outstanding[key].keys():
                        updating[key] = outstanding[key]
                        updating[key]['update-start'] = date
                        del outstanding[key]

                    
        
             
        if (lncount % 1000 == 0):
            print "On line " + str(lncount)
        lncount = lncount + 1


def parse_date(datestring):
    return datetime.datetime.strptime(datestring, "%Y-%m-%d %H:%M:%S,%f")
            
            
        
        


if __name__ == "__main__":

    inputfile = open('/home/mininet/netassay-optimization/netassay.log', 'r')
    outfilename = time.strftime("/home/mininet/netassay-optimization/pyretic/modules/netassay/eval/output/%Y%m%d-%H%M%S-parsed.csv")
    outputfile = open(outfilename, 'w+')

    parse_file(inputfile,outputfile)
    inputfile.close()
    outputfile.close()
               
