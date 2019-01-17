import shutil, sqlite3, sys, time, urllib
from os.path import getmtime
from subprocess import Popen, PIPE
from xml.dom.minidom import Document

def pack(title, subtitle='', uid=None, arg='', icon="icon.png",
        autocomplete='', valid=None):
    if uid is None:
        uid = UID+'.'+str('.'.join(title.split()))
    else:
        uid = unicode(uid)
        if not uid.startswith(UID):
            uid = UID+'.'+uid
    if arg and valid is None:
        valid = True
    return (title, subtitle, arg, uid, icon, autocomplete,
#           0      1         2    3    4     5             6
               "yes" if valid else "no")
def sendMessages(l):
    doc = Document()
    items = doc.createElement("items")
    for i in l:
        item = doc.createElement("item")
        item.setAttribute("uid", i[3])
        item.setAttribute("arg", i[2])
        item.setAttribute("valid", i[6])
        attr = doc.createElement("title")
        attr.appendChild(doc.createTextNode(i[0]))
        item.appendChild(attr)
        attr = doc.createElement("subtitle")
        attr.appendChild(doc.createTextNode(i[1]))
        item.appendChild(attr)
        attr = doc.createElement("icon")
        attr.appendChild(doc.createTextNode(i[4]))
        item.appendChild(attr)
        items.appendChild(item)
    doc.appendChild(items)
    print unicode(doc.toxml()).encode('utf-8')
def sendMessage(v):
    sendMessages((v,))

USER,_ = Popen("whoami", stdout=PIPE).communicate()
HISTORY_CHROME = "/Users/%s/Library/Application Support/Google/Chrome/Default/History"%USER.strip()
HISTORY_LOCAL = "chrome_history.db"
UID = "com.gmail.at.mrchenyu.ChromeHistory"

CACHE_LIFE = 90
def checkCache():
    try: updateTime = getmtime(HISTORY_CHROME)
    except OSError:
        raise Exception("Unable to find Chome history data")
    try: cacheTime = getmtime(HISTORY_LOCAL)
    except OSError: cacheTime = 0
    if updateTime < cacheTime:
        return
    if updateTime - cacheTime < CACHE_LIFE:
        return
    if time.time() - cacheTime < CACHE_LIFE:
        return
    shutil.copyfile(HISTORY_CHROME, HISTORY_LOCAL)

def search(w, q, others):
    db = sqlite3.connect(HISTORY_LOCAL)
    db.row_factory = sqlite3.Row
    cursor = db.execute('SELECT * FROM urls '+ w +
            'ORDER BY last_visit_time DESC', *q)
    def makeResult():
        for _ in range(10):
            r = cursor.fetchone()
            while True:
                if r is None: return
                for q in others:
                    if  r['title'].upper().find(q)<0 and \
                            r['url'].upper().find(q)<0:
                        break
                else:
                    yield r
                    break
                r = cursor.fetchone()
    return list(makeResult())

def parseQuery(q):
    s = 0
    for c in q.decode('utf-8'):
        if s==0:
            if c=='\\':
                s,r = 2,''
            elif c!=' ':
                s,r = 1,c
        elif s==1:
            if c=='\\':
                s = 2
            elif c!=' ':
                r += c
            else:
                yield r
                s = 0
        elif s==2:
            r += c
            s = 1
    if s==1:
        yield r
    elif s==2:
        yield r+'\\'

def wildcardEscape(s):
    return ''.join('\\'+i if i in "\\%_" else i for i in s)
def process(query):
    checkCache()
    # parse query
    if query:
        queries = list(parseQuery(query))
        query = ', '.join('"'+q+'"' for q in queries)
        queries.sort(key=lambda x:-len(x))
        t, queries = queries[0], [q.upper() for q in queries[1:]]
        t = (wildcardEscape(t),
                wildcardEscape(urllib.quote(t.encode('utf-8'))))
        q = (['%'+i+'%' for i in t],)
        w = 'WHERE title LIKE ? ESCAPE "\\" OR url LIKE ? ESCAPE "\\" '
    else:
        q,w,queries = (),'',[]
    l = search(w, q, queries)
    # generate output
    if not l:
        sendMessage(pack("No Result" if query else "No Access",
            "No websites contained: "+query if query else
                    "Unable to access Chrome history data",
            "no_result"))
    else:
        sendMessages(pack(i['title'] or i['url'], i['url'],
            'result.'+str(i['id']), i['url']) for i in l)

def main(query):
    try: process(query)
    except Exception as e:
        import traceback; traceback.print_exc()
        sendMessage(pack('Hi, there! We have a problem.', str(e)))

if __name__ == '__main__':
    main(' '.join(sys.argv[1:]))

