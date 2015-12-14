##TESTED ON MYSQL 2 - REQUIRES THESE MODULES: mechanize,  bs4, and MySQLdb modules.


##SETTINGS##
freq=60 # how often to check in seconds; will automatically sleep for 5 seconds after checking each post to avoid being blocked by PHPBB
cron=True # if making cronjob, set this to True; will only loop once, and freq will be ignored
username='' # TLS USERNAME FOR BOT
password='' #TLS PASSWORD FOR BOT
forums_to_check=['9'] # FORUMS TO CHECK - 9 = my chances (f=? in url of each forum)
dir='/home/rob/tlsbot/' # FULL DIRECTORY THAT BOT IS IN
urms={'URM, Exclude AA':['MA','Mexican','Latino','PR','latina','puerto','rican','native'],'AA Only':['aa','african','afam'],'Only':['urm'],'Include':[]} #URM recognition values

#MYSQL INFORMATION IS TO COORDINATE WITH MYLSN GRAPHS. CAN REMOVE MYSQL INFORMATION BY LEAVING THE VARIABLES BELOW UNCHANGED

mysql_host=''
mysql_user=''
mysql_password=''
mysql_db=''

##DO NOT EDIT BELOW THIS LINE UNLESS YOU KNOW WHAT YOU ARE DOING##

import mechanize,  time, cookielib, datetime, re, MySQLdb, random, string, json
from bs4 import BeautifulSoup
if mysql_host != '':
	db=MySQLdb.connect(host=mysql_host,user=mysql_user,passwd=mysql_password,db=mysql_db)
	db.autocommit(True) # Rather than reconnecting on each loop
	cur=db.cursor()

def getImageLink(lsat,gpa,urm,ed):
	global mysql_host
	if mysql_host != '':
		cont=False
		while not cont:
			random_string=''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
			cur.execute("""select %s from %s where %s="%s" limit 1;""" % ('searchkey','saved_searches','searchkey',random_string))
			a=cur.fetchall()
			if len(a) == 0: cont=True
		search_params={"formsubmitted":"1","searchtype":"automatic","lsat":str(lsat),"gpa":str(gpa),"urm":urm,"ed":ed,"submitted1":"Show all","submitted2":"Show all","automatic":"yes","botpost":True}
		cur.execute("""INSERT INTO  %s (`%s` ,`%s`,`%s`)VALUES ("%s",  "%s",  "%s");""" % ('saved_searches', 'searchkey','newvars','results',random_string,MySQLdb.escape_string(json.dumps(search_params)),''))	
		return random_string
	else: return ''

	
def process_post(post_content_page):
	post_content=post_content_page.find('div',{'class':'content'}).getText()
	title=post_content_page.find('h2',{'class':'topic-title'}).getText()
	#print 'http://www.top-law-schools.com/forums/viewtopic.php?f='+forum+'&t='+tid
	num_posts=int(post_content_page.find('dd',{'class':'profile-posts'}).getText().replace('Posts:','').replace(' ',''))
	#lsats=re.findall(r'([\/| ][0-9]{3}[\.| |\/|l|L])',post_content) #recognizes: " XXX ", " XXX.", " XXX/", "/XXX","XXXlsat"
	#gpas=re.findall(r'([\/| ][0-9]\.[0-9]{1,4}[\.| |\/|g|G])',post_content) #recognizes: " X.X(XXX) ", " X.X(XXX)/", "/X.X(XXX) ","X.X(XXX)gpa"
	c=0
	while c < 2:
		c+=1
		lsats=re.findall(r'([0-9]{3})',title) #recognizes: " XXX ", " XXX.", " XXX/", "/XXX","XXXlsat"
		gpas=re.findall(r'([0-9]\.[0-9]{1,4})',title) #recognizes: " X.X(XXX) ", " X.X(XXX)/", "/X.X(XXX) ","X.X(XXX)gpa"
		if len(lsats) ==0 and len(gpas) ==0: title=title+' '+post_content
		else: c=2
	if len(lsats) == 0 or (len(lsats) == 2 and len(re.findall(r'([0-9]{3}\-[0-9]{3})',post_content)) > 0) or len(lsats) > 4: 
		lsats=re.findall(r'([0-9]{3}\-[0-9]{3})',post_content) # check if there are LSAT ranges
		if len(lsats) == 1: # if there is one such range, take the average of the range
			lsats=lsats[0].split('-')
			lsats=[str(int((float(lsats[0])+float(lsats[1]))/2))]
	if len(gpas) == 0 or (len(gpas) == 2 and (len(re.findall(r'([0-9]\.[0-9]{1,4}\-[0-9]\.[0-9]{1,4})',post_content)) > 0)) or len(gpas) > 4: 
		gpas=re.findall(r'([0-9]\.[0-9]{1,4}\-[0-9]\.[0-9]{1,4})',post_content) # check if there are LSAT ranges
		if len(gpas) == 1: # if there is one such range, take the average of the range
			gpas=gpas[0].split('-')
			gpas=[str(round((float(gpas[0])+float(gpas[1]))/2,2))]
	highest_lsat=0
	highest_gpa=10 # actually lowest GPA - I've found that people seem to list all of their GPA's when their LSAC GPA is their lowest
	if len(gpas) <= 4 and len(lsats) <= 4: # if more than 4 GPA's or LSAT's, I don't know what's going on
		for lsat in lsats:
			# remove all non-digit characters
			lsat=int(re.sub("\D", "", lsat))
			if lsat > highest_lsat and lsat > 120 and lsat < 181: highest_lsat=lsat
		for gpa in gpas:
			# remove all non-digit characters:
			gpa=re.sub("\D","",gpa)
			gpa=float((gpa[:1]+'.'+gpa[1:])[:4]) #reformat properly, remove extra precision
			if gpa < highest_gpa and gpa > 2 and gpa < 4.4: highest_gpa=gpa
	urm='Exclude'
	for urmv in urms:
		for matchval in urms[urmv]:
			if post_content.lower().count(' '+matchval.lower()+' ') != 0 or post_content.lower().count(' '+matchval.lower()+'.') != 0:
				urm=urmv
	ed='Exclude'
	if post_content.lower().count(' ed ') != 0 or post_content.lower().count('early decision') != 0: ed='Only'
	return {'lsat':highest_lsat,'gpa':highest_gpa,'urm':urm,'posts':num_posts,'ed':ed}

def generate_reply(lsat,gpa,urm,num_posts,ed):
	reply_text=[]
	if num_posts < 10: reply_text.append('Welcome to TLS!')
	if gpa == 10 or lsat == 0: reply_text.append("It doesn't look like you've told us your LSAT and GPA. Many factors might affect your law school applications, but most TLS users agree that LSAT and GPA are usually the two most important. Please edit your post to include your LSAT and LSAC GPA. If you have not yet taken the LSAT, a range of practice test scores is okay, too.")
	else:
		image_link=getImageLink(lsat,gpa,urm,ed)
		# ONCE CAN POST IMAGES: reply_text.append("Since you've provided your LSAT ("+str(lsat)+") and GPA ("+str(gpa)+"), I have generated an image with an overview of relevant admissions data on [url=http://lawschoolnumbers.com]LawSchoolNumbers.com[/url].\n\nHere is your image: http://mylsn.info/"+image_link+"_1-14.jpg")
		reply_text.append("Since you've provided your LSAT ("+str(lsat)+") and GPA ("+str(gpa)+"), I have generated a graph with an overview of relevant admissions data on [url=http://lawschoolnumbers.com]LawSchoolNumbers.com[/url].\n\nHere is your image: http://mylsn.info/"+image_link)
	reply_text.append("Other useful links:\n[list][*][url=http://lawschoolnumbers.com]LawSchoolNumbers[/url]: Self-Reported Law School Admissions Data\n[*][url=http://mylsn.info]MyLSN[/url]: Aggregates Data from LawSchoolNumbers.com\n[*][url=http://www.lawschoolpredictor.com/wp-content/uploads/Law-School-Predictor-LSDAS-GPA-Calculator.htm]LSAC GPA Calculator[/url]: most TLS'ers consider LSAC GPA to be the most important measure of GPA\n[*][url=http://www.lstscorereports.com/national/]LawSchoolTransparency[/url]: Law School Employment Data[/list]")
	reply_text.append("This post is just meant to provide you with a bit of helpful starting information. Hopefully more users will be along shortly to help you more.")
	reply_text.append("[size=85][i]I am a bot, but my inbox is actively monitored. If you have any questions, comments, suggestions, or criticisms, please send a message to this account. I can not yet post images, but when I reach 100 posts I will post them instead of links.[/i][/size]")	
	reply_text="\n\n".join(reply_text)
	return reply_text
	
	
def doPost(forum,tid,reply_text):
	reply_page=br.open('http://www.top-law-schools.com/forums/posting.php?mode=reply&f='+forum+'&t='+tid).read()
	br.select_form(nr=0)
	br.form['message']=reply_text
	time.sleep(5)
	#br.submit(name='post',label='Submit')
	br.submit(nr=1)

br = mechanize.Browser()
cj = cookielib.LWPCookieJar()
br.set_cookiejar(cj)
br.set_handle_equiv(True)
#br.set_handle_gzip(True)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)
br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
br.addheaders = [('User-agent', 'TLS Bot, see http://mylsn.info/tlsbot.txt for more information.')]

# Open some site, let's pick a random one, the first that pops in mind:
r = br.open('http://www.top-law-schools.com/forums/ucp.php?mode=login')
html = r.read()
br.select_form(nr=0)

# Let's search
br.form['username']=username
br.form['password']=password
br.find_control('autologin').items[0].selected=True
#br.form['autologin'].selected=True
br.submit()
br.response().read()

keepGoing=True

while keepGoing:
	for forum in forums_to_check: #9 = what are my chances
		page=BeautifulSoup(br.open('http://www.top-law-schools.com/forums/viewforum.php?f='+forum).read())
		
		#BEGIN PAGE PROCESSOR
		
		#checked_posts=open(dir+'checked_posts').read().split(',') # in case we ever need it; since most_recent check is based off of topic_id, do not need this; but may need it in future
		most_recent_check=open(dir+'most_recent_check').read().strip() # rather than using time, I use topic ID, which appears to be sequential
		start_most_recent_check=most_recent_check
		posts=page.findAll('div',{'class':'list-inner'})
		for post in posts:
			if post.getText().strip() != 'Topics': # first reference is headings, ignore this line
				tid=str(post.find('a',{'class':'topictitle'}))
				tid=tid[tid.find('t=')+2:tid.find('">')]# topic id
				date=post.find('div',{'class':'responsive-hide'}).getText().replace('&raquo;','').strip() # in case we ever need it, but for now I just use topic ID
				if int(tid) > int(start_most_recent_check): # was this thread posted after the most recent one we checked?
					if int(tid) > int(most_recent_check): most_recent_check=tid # update most recently checked thread
					post_data=process_post(BeautifulSoup(br.open('http://www.top-law-schools.com/forums/viewtopic.php?f='+forum+'&t='+tid).read())) # FIGURE OUT LSAT, GPA, URM
					reply_text=generate_reply(post_data['lsat'],post_data['gpa'],post_data['urm'],post_data['posts'],post_data['ed']) # GENERATE REPLY TEXT
					doPost(forum,tid,reply_text) # POST REPLY TEXT
					time.sleep(2)
		if start_most_recent_check != most_recent_check: open(dir+'most_recent_check','w').write(most_recent_check) # update latest topic id checked for future runs
		if not cron: time.sleep(freq)
		
		#END PAGE PROCESSOR
	if cron: keepGoing=False