
DOMAIN_LIST = "alexa-top-100-2014-12-03.txt"

def get_list_of_domains():
    f = open(DOMAIN_LIST, 'r')
    domain_list = []
    for line in f:
        domain_list.append(line.strip())
    f.close()
    return domain_list
    
