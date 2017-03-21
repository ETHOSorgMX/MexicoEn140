
#! /usr/bin/python
# -*- coding: utf8 -*-


"""
Master Collector for MX140 v1.0
-------------- ----------------
"""

#from __future__ import unicode_literals
import logging
import twitter, twython
import json, cPickle
import tokenizer
import os
from collections import Counter
import time, random
import git
from datetime import datetime
from email.utils import parsedate_tz, mktime_tz
from logging.handlers import RotatingFileHandler
import smtplib
import configparser

#Config logger configurations
# create logger with 'master_collector'
logger = logging.getLogger('master_collector')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh_d = RotatingFileHandler('logs/master_collector.log', maxBytes=5120)
fh_d.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh_d.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh_d)

# ------------------------------------------------ ------------------------------------------------>
# ------------------------------------------------>
def dual_login(app_data, user_data):
    """
    login, oauthdance and creates .credential file for specified user
    """
    APP_NAME = app_data['AN']
    CONSUMER_KEY = app_data['CK']
    CONSUMER_SECRET = app_data['CS']
    CREDENTIAL = '.'+user_data['UN']+'.credential'
    #Autenthicate twitter Oauth
    try:
        (oauth_token, oauth_token_secret) = twitter.oauth.read_token_file(CREDENTIAL)
        logger.info('[Load]: %s' % CREDENTIAL)
    except IOError, e:
        (oauth_token, oauth_token_secret) = twitter.oauth_dance(APP_NAME, CONSUMER_KEY, CONSUMER_SECRET)
        twitter.oauth.write_token_file(CREDENTIAL, oauth_token, oauth_token_secret)
        logger.info('[SAVE]: %s' % CREDENTIAL)

    if len(oauth_token) == 0:
        logger.error("Error getting apis connection twitter..")
        notifyByEmail('No se pudo conectar al api de twitter, revisar las credenciales.')
        return
    else:
        api1 = twitter.Twitter(domain='api.twitter.com', api_version='1.1', auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret, CONSUMER_KEY, CONSUMER_SECRET))
        api2 = twython.Twython(CONSUMER_KEY, CONSUMER_SECRET, oauth_token, oauth_token_secret)
        return api1, api2

def notifyByEmail(messageError):
    try:
        lastNotification = cPickle.load(open("lastNotification.cpk", 'r'))
    except Exception as e:
        logger.error("Error loading lastNotification.cpk: " +  str(e))
        lastNotification = datetime(2017, 1, 1, 0, 0)
    today = datetime.today()
    ts_lastNotification = time.mktime(lastNotification.timetuple())
    ts_today = time.mktime(today.timetuple())

    period = int(ts_today-ts_lastNotification) / 3600
    if period > 2:
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')

            email_user = config.get('NOTIFICATION', 'email_user')
            email_password = config.get('NOTIFICATION', 'email_password')
            email_server = config.get('NOTIFICATION', 'email_server')
            email_port = config.getint('NOTIFICATION', 'email_port')
            email_to = config.get('NOTIFICATION', 'email_to')

            fromEmail = email_user
            subject = config.get('NOTIFICATION', 'email_subject')

            server = smtplib.SMTP(email_server, email_port)
            server.ehlo()
            server.starttls()
            #Next, log in to the server
            server.login(email_user, email_password)
            #Send the mail
            msg = "\n Reporte de error: \n" + messageError
            emailText = """\
From: %s  
To: %s  
Subject: %s

%s
""" % (fromEmail, to, subject, msg)
            server.sendmail(fromEmail, to, emailText)
            server.close()

            cPickle.dump(lastNotification, open('lastNotification.cpk', 'w'))
        except Exception as e:
            logger.error("Error loading Email: " +  str(e))
    return

def do_log(dat_file=".mx140.dat"):
    # login
    global api01, api02
    app_data, user_data = cPickle.load(open(dat_file, 'r'))
    api01, api02 = dual_login(app_data, user_data)
    return

def do_checkpath():
	# pathchek
    global out_dir, NODE_PROJECT_PATH
    out_dir = "out/"
    NODE_PROJECT_PATH = "../AppNode/"
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    if not os.path.exists(NODE_PROJECT_PATH): 
    	print 'Required Node_Project_Path for execution'
    	logger.error('Required Node_Project_Path for execution')
    	raise SystemExit
    return


def fetch_tweets_from_list(owner_screen_name="MX_en140",\
			slug="mx140-opinion",\
			include_entities="false",\
			count="200",\
			since_id="600000000000000000",\
			max_id="0"):
	"""
	fetches all more recent tweets from a given list
	returns a batch list with all more recent twitter status objects
	"""
	#global very_last_id
	batch = []
	# primer collect, trata de traerlos todos
	try:
		new_statuses = api01.lists.statuses(owner_screen_name=owner_screen_name,\
											slug=slug,\
											include_entities=include_entities,\
											count=count,\
											since_id=since_id)
		if (len(new_statuses) > 2):
			batch.extend(new_statuses)
			max_id = new_statuses[-1]["id"]-1
			# update the since_id
			very_last_id = new_statuses[0]["id"]
			logger.info("[get]:" + str(len(new_statuses)) + " new statuses")
			logger.info("\t\tfrom:" + str(new_statuses[-1]["id"]) + " created at:" + str(new_statuses[-1]["created_at"]))
			logger.info("\t\tto:" + str(new_statuses[0]['id']) + " created_at:" + str(new_statuses[0]["created_at"]))			
		else:
			logger.info("[get]:" + str(len(new_statuses)) + " new statuses")
			logger.error("\t\tCan get enought tweets")
	except Exception as e: 
		logger.error(str(e))
		logger.debug("[FAIL]: max_id = " + str(max_id) + " in slug: " + slug)
		new_statuses = []
	# una vez hecho el primer collect, trae mas
	while(len(new_statuses)>2):
		try:
			new_statuses = api01.lists.statuses(owner_screen_name=owner_screen_name, \
												slug=slug, \
												include_entities=include_entities, \
												count=count, \
												since_id=since_id, \
												max_id=max_id)
			batch.extend(new_statuses)
			max_id = new_statuses[-1]["id"]-1
			loger.info("[get]:" + str(len(new_statuses)) + " new statuses")
			logger.info("\t\tfrom:" + str(new_statuses[-1]["id"]) + "created at:" + str(new_statuses[-1]["created_at"]))
			logger.info("\t\tto:" + str(new_statuses[0]['id']) +  "created_at:" +  str(new_statuses[0]["created_at"]))
		except:
			logger.error("[FAIL]: max_id = " +  str(max_id) + " in slug: " + slug)
			new_statuses = []
			break
	# before leave, update marks
	batch.reverse()
	return batch


def count_words(texts_batch, stopwords = []):
	"""
	tokenize, count and filter stop words from a batch of texts
	return a counter or dictionary object
	"""
	tokens = []
	T = tokenizer.Tokenizer()
	# tokenize
	for text in texts_batch:
		tokens.extend(T.tokenize(text))
	# count
	C = Counter(tokens)
	# filter
	for sw in stopwords:
		if C.has_key(sw): C.pop(sw)
	for k in C.keys():
		if len(k)<4: C.pop(k)
	return C



def enlight_bag(bag=[]):
	"""
	select only interesting attributes of the status object, enlightening it
	"""
	newbag = [{'t':s['text'], \
				'u':s['user']['screen_name'], \
				'n':s['user']['name'], \
				'i':s['user']['profile_image_url'], \
				'c':str(datetime.fromtimestamp(mktime_tz(parsedate_tz(s['created_at']))))[5:], \
				'l':u"https://twitter.com/"+s['user']['screen_name']+u"/status/"+s['id_str']\
				} for s in bag]
	return newbag

container = """
<div class="twcontainer">
 	<img src="TOKEN_I" alt="TOKEN_N" style="float:left; margin:0 15px 20px 0;" />
	<table>
    	<tr> 
    		<td>
    			<a class="name" href="https://twitter.com/TOKEN_U" target="_blank">TOKEN_N</a>
    		</td> 
    	</tr>
    	<tr> 
    		<td>
    			<span class="screenname">
    				<a href="https://twitter.com/TOKEN_U" target="_blank">@TOKEN_U</a>
    			</span>
    			<span class="createdtime"> 
    				<a href="TOKEN_L" target="_blank">TOKEN_C</a> 
    			</span>
    		</td>
    	</tr>
    	<tr> <td class="tweettext">TOKEN_T</td> </tr>
  	</table>
  	<hr>
</div>
"""
titler = """
<div class="tooltiphead">
        <div class="toptitle">
        		<div><a target="_blank" href="https://twitter.com/search?q=TOKEN_H" class="spantitle">
        			<span>TOKEN_H</span></a>
        		</div>
    			<div><a href="#">
    				<span class="spancount">TOKEN_O</span>
    				<br>
    				<span class="spanmenc">menciones</span></a>
    			</div>
        </div>
</div>
"""
ender="""
<div class="twend">
	<div>
		<span class="ender1">Palabras Asociadas:</span><br><br>
		<span class="ender2">TOKEN_RW</span>
	</div>
</div>
"""
# ------------------------------------------------>
# ------------------------------------------------ ------------------------------------------------>



if __name__ == '__main__':

	do_checkpath()
	do_log()

	if api01 is not None:
	    list_of_lists =  ["mx140-ejecutivo", \
					"mx140-gobernadores", \
					"mx140-opinion", \
					"mx140-senadores", \
					"mx140-diputados", \
					"mx140-pri", \
					"mx140-pan", \
					"mx140-prd"]
	    rlis = {"mx140-ejecutivo":"poder ejecutivo", \
				"mx140-gobernadores":"gobernadores", \
				"mx140-diputados":"diputados", \
				"mx140-senadores":"senadores", \
				"mx140-opinion":"lideres de opinion", \
				"mx140-pri":"pri", \
				"mx140-pan":"pan", \
				"mx140-prd":"prd"}


	    most_recent_ids = {l:"600000000000000000" for l in list_of_lists}
		#buffers = {l:[] for l in list_of_lists}; cPickle.dump (buffers, open('buffers.cpk','w'))
		#stopwords = [w.strip().rstrip() for w in open('nsw.txt','r').readlines()]
		
		#Comment by U8
	    stopwords = [w.strip().rstrip().decode('utf8','ignore') for w in open('stopwords.txt','r').readlines()]
		#End Comment by U8

		#print stopwords
	    max_buffer_size = 10000
	    max_most_common_words = 30
	    min_bag_size = 1
	    max_status_buffsize = 10

	    while(True):
			# init and load datastructs
			pack_json = {}
			pack_statuses = {}
			all_batch = []
			try:
				buffers = cPickle.load(open("buffers.cpk",'r'))
			except Exception as e: 
				logger.error("Error loading buffer.cpk: " +  str(e))
				buffers={}
			try:
				most_recent_ids = cPickle.load(open("mrids.cpk",'r'))
			except Exception as e: 
				logger.error("Error loading mrids.cpk: " +  str(e))
				most_recent_ids = {}
			try:
				status_buff = cPickle.load(open('status.buff','r'))
			except Exception as e: 
				logger.error("Error loading status.buff: " +  str(e))
				status_buff = {}
			
			# fill from lists
			for l in list_of_lists:
				pack_json[l] = {}
				default_since = "600000000000000000"
				most_recent_ids.setdefault(l, default_since)

				# get all available messages

				#Adding 1 to slug for match with list name in twitter
				batch = fetch_tweets_from_list(owner_screen_name="MX_en140",\
											slug=l + "1",\
											include_entities="false",\
											count="200",\
											since_id=most_recent_ids[l],\
											max_id="0")
				# update most_recent_ids
				try:
					most_recent_ids[l] = batch[-1]['id_str']
				except:
					logger.error('Can not get last index for: ' + l)
					most_recent_ids[l] = most_recent_ids[l]

				logger.debug("[batch]: " + str(l) + " - " + str(len(batch)) + " - " + str(most_recent_ids[l]))
			
				# store on buffers
				pack_statuses[l] = batch
				all_batch.extend(batch)
				new_texts = [s['text'].lower() for s in batch]

				try:
					buffers[l].extend(new_texts)
				except: 
					buffers[l] = new_texts;

				if ( len(buffers[l])>max_buffer_size ):
					buffers[l] = buffers[l][-max_buffer_size:]
				try:
					buffers['all'].extend(new_texts)
				except:
					buffers['all'] = new_texts

				if ( len(buffers['all'])>max_buffer_size ):
					buffers['all'] = buffers['all'][-max_buffer_size:]
				logger.debug("[buffer]: " + str(l) + " - " + str(len(buffers[l])) + " - " + str(len(new_texts)))

				#count words
				C = count_words(buffers[l], stopwords)
				top_words = C.most_common(max_most_common_words)

				#select messages for each selected word
				bag = []
				#if len(top_words)>0: top_words.reverse()
				for (w,c) in top_words:
					# the bag contains current status with top words
					try:
						bag = [s for s in batch if w in s['text'].lower()]
					except:
						bag = []
					
					pack_json[l][w] = c#{"count": c, "bag":[]}

					# here you filter and administrate messages buffer
					# here you can make dynamic assignments
					
					# so pack only words with enough pressence, enlight the bag
					if ((len(bag)>=min_bag_size) or (len(bag)==0)):
						#pack_json[l][w] = c#{"count": c, "bag":bag[:min_bag_size]}
						lightbag = enlight_bag(bag)
						try:
							status_buff[l][w].extend(lightbag)
						except:
							status_buff.setdefault(l, {});
							status_buff[l][w] = lightbag
						# crop status_buff
						if len(status_buff[l][w])>max_status_buffsize: 
							status_buff[l][w] = status_buff[l][w][-max_status_buffsize:]
					#elif len(bag)==0:
					#	pack_json[l][w] = c#{"count": c, "bag":[]};			

			# for the all buffer
			C = count_words(buffers['all'], stopwords)
			top_words = C.most_common(max_most_common_words)
			pack_json['all'] = {w: c for (w,c) in top_words}
			
			for (w,c) in top_words:
				try:
					bag = [s for s in all_batch if w in s['text'].lower()]
				except:
					bag = []
				pack_json['all'][w] = c
				if ((len(bag)>=min_bag_size) or (len(bag)==0)):
					#pack_json['all'][w] = c#{"count": c, "bag":bag[:min_bag_size]}
					lightbag = enlight_bag(bag)
					try:
						status_buff['all'][w].extend(lightbag)
					except:
						status_buff.setdefault('all', {})
						status_buff['all'][w] = lightbag
					# crop status_buff
					if len(status_buff['all'][w])>max_status_buffsize: 
						status_buff['all'][w] = status_buff['all'][w][-max_status_buffsize:]
			

			# create containers for all the classes
			containers={}
			#select random list for status update
			current_list = random.choice(list_of_lists)
			current_keyword= ""
			current_asoc_ws = []

			for k in status_buff.keys():
				containers[k]={}
				if k==current_list: 
					current_keyword = random.choice(pack_json[current_list].keys())
				for w in status_buff[k].keys():
					if w in pack_json[k].keys():
						containers[k][w] = []
						# cross the array backwards and make containers
						for s in reversed(status_buff[k][w]):
							newC = container.replace('TOKEN_I',s['i']).replace('TOKEN_L',s['l']).replace('TOKEN_C',s['c'])
							newC = newC.replace('TOKEN_N',s['n']).replace('TOKEN_T',s['t']).replace('TOKEN_U',s['u'])
							containers[k][w].append(newC)
						# get most_common related words
						txstat = [s['t'].lower() for s in status_buff[k][w]]
						miniC = count_words(txstat, stopwords)

						if w==current_keyword:
							try: 
								current_asoc_ws= [cws for (cws,co) in miniC.most_common(6)[1:]]
							except:
								current_asoc_ws= [[cws for (cws,co) in miniC.most_common(6)]]
						related_words = ', '.join([cws for (cws,co) in miniC.most_common(6)[1:]])
						#form complete qtip content
						containers[k][w] = titler.replace('TOKEN_H', w.upper()).replace('TOKEN_O',str(pack_json[k][w]))+'<hr>'+('\n'.join(containers[k][w]))+ender.replace('TOKEN_RW', related_words)
			
			df = open(NODE_PROJECT_PATH + 'public/js/containers.js','w')

			print >>df, "var tts = "+json.dumps(containers)+";"
			df.close();



			# save files and states
			json.dump(pack_statuses, open(out_dir+"mx140"+"-"+time.asctime()+".json",'w'))
			json.dump (pack_json, open('pack.json','w'))
			nf = open(NODE_PROJECT_PATH + 'public/js/data.js','w')
			print >>nf, "var data = "+json.dumps(pack_json)+";"
			nf.close()
			cPickle.dump (buffers, open('buffers.cpk','w'))
			cPickle.dump (most_recent_ids, open('mrids.cpk','w'))
			cPickle.dump (status_buff, open('status.buff','w'))
			logger.info("[saved]: pack.json, buffers.cpk, mrids.cpk, status.buff")

			
			try:
				current_status = u"El grupo de " + \
							rlis[current_list].upper() + \
							u" discute sobre "+ \
							current_keyword.upper() +\
							u" junto a [ " +\
							current_asoc_ws[1] + " ] y [ " +\
							current_asoc_ws[3] +\
							u" ]. [+] en http://mexicoen140.org.mx"
				if len(current_status)<127:
					current_status+=u" #M\u00C9XICOen140"
				ok_status = api01.statuses.update(status=current_status)
				logger.info("Status publish: " + current_status + str(ok_status['text']))
			except twitter.TwitterHTTPError as e:
				logger.error("Error publishing: " + current_status + " error: " + str(e))
			current_keyword= ""
			current_asoc_ws = []
	else:
	    logger.error("[Twitter]: API can not connect")
	#now procceed to sleep to start again later
	logger.info("[sleeping]:" + time.asctime())
	print "[sleeping]:", time.asctime()
	time.sleep(601)
