#!/usr/bin/env python 
import sys
import os
import commands
import re
import tempfile
import socket

MODPATH = os.path.realpath(os.path.split(__file__)[0])
USERMAIL_FILE = os.path.join(MODPATH,"user2mail")
DEFAULT_MAIL = "cgenomics+error@gmail.com"

try:
    jobid = sys.argv[1]
except IndexError: 
    jobid = None

try:
    taskid = int(sys.argv[2])
except (IndexError, ValueError): 
    taskid = None


if jobid: 
    try:
        jobinfo = commands.getoutput(". $SGE_ROOT/cgenomics/common/settings.sh && qstat -j %s" %jobid)
    except Exception:
        jobinfo = "Ooops, something went wrong when retrieving job info [%s]" %jobid
     

sendmail = True

# I need to know if this is part of an array job and if this is the
# last task to be finished (don't want email with each task).  First,
# I tried using a jobid file or sqlite database, but I found them to
# fail due to race conditions, file locking, etc. The solution is to
# keep an small daemon listeing on qmaster:6446 and keeps the coutner
# of done tasks. The following code asks the qarray daemon how many
# tasks have been completed with the same jobid. 
if jobid and taskid:
    # crea un socket INET de tipo STREAM
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # ahora se conecta al servidor web en el puerto 80 (http)
    s.connect(("qmaster", 6446))
    s.send("%s" %jobid)
    try:
        donetasks, totaltasks = map(int, s.recv(16).split("|"))
    except Exception, e: 
        sendmail = False
        print >>sys.stderr, e
    else:
        print >>sys.stderr, "SGE:", "array job - Done %s Total %s" %(donetasks, totaltasks)
        if donetasks != totaltasks:
            sendmail = False

if sendmail: 
    try: 
        print >>sys.stderr, "SGE:", ". $SGE_ROOT/cgenomics/common/settings.sh && qsummary %s" %jobid
        summary = commands.getoutput(". $SGE_ROOT/cgenomics/common/settings.sh && qsummary %s" %jobid)
    except Exception:
        summary = "Ooops, something failed retrieving job summary. If your job was not an array job, try running qsummary now."

    m = re.search("owner:\s(.+)", jobinfo, re.MULTILINE)
    if m:
        owner = m.groups()[0].strip()
        user2mail = dict([ map(strip, line.strip()) for l in  open(USERMAIL_FILE)])
        email = user2mail.get(owner, DEFAULT_EMAIL)
    else:
        email = DEFAULT_EMAIL


    F = tempfile.NamedTemporaryFile()
    F.write(summary)
    F.write(jobinfo)
    F.flush()
    
    ss = os.system('''/usr/bin/mail -s "Work %s is done (last task=%s)" %s < %s''' %(jobid, taskid, email, F.name))

    print >>sys.stderr, "SGE: Mail sent", email, jobid, taskid, ss
    print >>sys.stderr, open(F.name).read()
    print >>sys.stderr, summary
    print >>sys.stderr, jobinfo

    sys.stderr.flush()
    F.close()
else:
    print >>sys.stderr, "SGE: Mail not sent", jobid, taskid

