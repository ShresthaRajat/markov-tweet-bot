from markov_model import MarkovModel
from utility import Utility
import twitter
import time
from threading import Thread, Lock

class Tweeter:
    
    def __init__(self):

        # Tweet pesistance

        self._last_tweet_in = None
        self._last_tweet_out = None

        # Auto Reply attributes
        self._targetstring = None
        
        self._auto_keywords = None
        self._auto_tweetprefix = None
        self._auto_tweetsuffix = None
    
        self._maxconvdepth = None
        self._mindelay = None

        self._autoreply = False
        self._autotweet = False
        
        # Auto tweet attributes
        self._keywords = None
        self._tweetprefix = None
        self._tweetsuffix = None
    
        self._jitter = None
        self._interval = None

        # API Access
        self._oauth = None
        self._t_auth = None
        self._ts_auth =None

        self._credentials = None

        self._t_lock = Lock()
        self._ts_lock = Lock()

        # Thread related attributes
        self._areply_alive = True
        self._areply_thread = Thread(target = self._autoreply)
        self._areply_thread.daemon = True
        self._areply_thread.name = 'replier'

        self._tweet_alive = True
        self._tweet_thread = Thread(target = self._autotweet)
        self._tweet_thread.daemon = True
        self._tweet_thread.name = 'tweeter'

        self._examine_alive = True
        self._examine_thread = Thread(target = self._examine)
        self._examine_thread.daemon = True
        self._examine_thread.name = 'examiner'

        # Login
        self._logged_in = False

        # Start all threads
        self._areply_thread.start()
        self._tweet_thread.start()
        self._examine_thread.start()
    """
    Login to twitter using credentials provided
    """
    def login(self, c_key, c_secret, a_token, a_t_secret):
        self._oauth = twitter.OAuth(a_token, a_t_secret, c_key, c_secret)
        self._t_auth = twitter.Twitter(auth = self._oauth)
        self._ts_auth = twitter.TwitterStream(auth = self._oauth)
        self._logged_in = True

        self._credentials = self._t_auth.account.verify_credentials()

    """
    Start auto tweets
    """
    def start_tweeting(self, days =1, hours = 0, mins = 0, jitter = 0, keywords = None, prefix = None, suffix = None):
        for i in [days, hours, mins]:
            if i <= 0 or i == None: i = 0
        
        interval = (days * 1440) + (60 * hours) + mins
        if interval == 0: interval = 1440

        self._interval = interval
        self._jitter = jitter
        self._keywords = keywords
        self._prefix = prefix
        self._suffix = suffix

        self._autotweet = True

    """
    Stop auto tweets 
    """
    def stop_tweeting(self):
        self._interval = None
        self._jitter = None
        self._keywords = None
        self._prefix = None
        self._suffix = None

        self._autotweet = False

    """
    Auto reply sections start and end
    """
    def t_areply_start(self, targetstring, keywords=None, prefix=None, suffix=None, mindelay=1.5):

        self._targetstring = targetstring
        self._auto_keywords = keywords
        self._auto_tweetprefix = prefix
        self._auto_tweetsuffix = suffix
        self._mindelay = mindelay

        self._autoreply = True

    def t_areply_stop(self):
        self._autoreply = False
        self._targetstring = None
        self._auto_keywords = None
        self._auto_tweetprefix = None
        self._auto_tweetsuffix = None

    def get_prefix_in_reply(self, tweet):
        if self._tweetprefix == None:
            prefix = '@{0}'.format(tweet['user']['screen_name'])
        else:
            if type(self._tweetprefix) in [str]:
                prefix = '@{0} {1}'.format(tweet['user']['screen_name'], self._tweetprefix)
            elif type(self._tweetprefix) in [list, tuple]:
                prefix = '@{0} {1}'.format(tweet['user']['screen_name'], random.choice(self._tweetprefix))
            else:
                prefix = '@{0}'.format(tweet['user']['screen_name'])
                Utility.log('get_prefix_in_reply', 'Not using prefix')
        return prefix

    def get_suffix_in_reply(self):
        if self.tweetsuffix == None or type(self._tweetsuffix) in [str]:
            suffix = copy.deepcopy(self._tweetsuffix)
        elif type(self._tweetprefix) in [list, tuple]:
            suffix = random.choice(self._tweetsuffix)
        else:
            suffix = None
            Utility.log('get_suffix_in_reply', 'Not using suffix')

    @staticmethod
    def autoreply(self):
        while self._areply_alive:
            time.sleep(1)
            self.thread_monitor()
            if self._logged_in and self._targetstring != None:

                # Stuff with twitter stream
                self._ts_lock.acquire(True)
                it = self._ts_auth.statuses.filter(track = self._targetstring)
                self._ts_lock.release()

                while self._autoreply:
                    try:
                        tweet = it.next()
                    except StopIteration:
                        it = self._ts_auth.statuses.filter(track = self._targetstring)
                        continue
                    
                    self._last_tweet = copy.deepcopy(tweet)

                    if not self._autoreply:
                        continue

                    Utility.log('autoreply', 'New tweet found')
                    try:
                        Utility.log('autoreply', '{0} (@{1}): {2}'.format(tweet['user']['name'], tweet['user']['screen_name'], tweet['text']))
                    except:
                        Utility.log('autoreply', 'Unable to get characteristics of new tweet')

                    if tweet['user']['id_str'] == self._credentials['id_str']:
                        Utility.log('autoreply', 'Own Tweet')
                        continue
                    
                    if 'retweeted_status' in tweet.keys():
                        Utility.log('autoreply', 'Retweet')
                        continue
                    
                    inp_tweet = tweet['text'].split()
                    inp_tweet = TextProcessor.clean(inp_tweet)

                    seedword = []
                    if self._auto_keywords != None:
                        seedword = [word for word in self._keywords if word in inp_tweet]
                    
                    Utility.log('autoreply', 'Found seedwords {0}'.format(seedword))

                    prefix = self.get_prefix_in_reply(tweet)
                    suffix = self.get_suffix_in_reply()

                    response = self._construct_tweet(seedword = seedword, prefix=prefix, suffix = suffix)
                    
                    self._t_auth_lock.acquire(True)
                    
                    try: 
                        # resp = self._t_auth.statuses.update(status = response, 
                        # in_reply_to_status_id=tweet['id_str'],
							# in_reply_to_user_id=tweet['user']['id_str'],
							# in_reply_to_screen_name=tweet['user']['screen_name']
							# )
                        print(response)
                        Utility.log('autoreply', 'Posted reply: {0}'.format(response))
                        # self._last_tweet_out = copy.deepcopy(resp)
                    except e:
                        Utility.error('autoreply', 'Faile dto post reply: {0}'.format(e))
                    
                    self.t_auth_lock.release()
                    time.sleep(60.0 * self._mindelay)

    def get_prefix_in_tweet(self):        
        if self._auto_tweetprefix == None or type(self._tweetprefix) in [str]:
            prefix = copy.deepcopy(self._auto_tweetprefix)
        elif type(self._tweetprefix) in [list, tuple]:
            prefix = random.choice(self._auto_tweetprefix)
        else:
            prefix = None
            Utility.log('get_prefix_in_tweet', 'Not using prefix')


    def get_suffix_in_tweet(self):
        if self._auto_tweetsuffix == None or type(self._auto_tweetsuffix) in [str]:
            suffix = copy.deepcopy(self._auto_tweetsuffix)
        elif type(self._auto_tweetsuffix) in [list, tuple]:
            suffix = random.choice(self._auto_tweetsuffix)
        else:
            suffix = None
            Utility.log('get_suffix_in_tweet', 'Not using suffix')

    def _autotweet(self):
        while self._tweet_alive:
            time.sleep(1)
            self.thread_monitor()
            if self._logged_in and self._autotweet:
                
                keyword = None
                if(self._keywords != None):
                    if type(self.keywords) in [str]:
                        keyword = self.keywords
                    else:
                        keyword = random.choice(self._keywords)
                
                prefix = self.get_prefix_in_tweet()
                suffix = self.get_suffix_in_tweet()

                new_tweet = self._construct_tweet(seedword=keyword, prefix=prefix, suffix=suffix)

                self._t_auth_lock.acquire(True)

                try:
                    # tweet = self._t_auth.statuses.update(status = new_tweet)
                    Utility.log('autotweet', 'Wrote tweet: {0}'.format(new_tweet))
                    # self._last_tweet_out = copy.deepcopy(tweet)
                except Exception as e:
                    Utility.error('autotweet', 'Failed to post tweet: {0}'.format(e))
                    print(tweet)
                self._t_auth_lock.release()
                time.sleep(interval * 60)

    def _thread_monitor(self):
        if self._areply_alive:
            if not self._areply_thread.is_alive():
                Utility.log('thread_monitor', 'reply thread dead, reviving ...')

                self._areply_thread = Thread(target = self.autoreply)
                self._areply_thread.daemon = True
                self._areply_thread.name = 'replier'
                self._areply_thread.start()

                Utility.log('thread_monnitor', 'Restarted reply thread')

        if self._tweet_alive:
            if not self._tweet_thread.is_alive():
                Utility.log('thread_monitor', 'tweet thread dead, reviving ...')

                self._tweet_thread = Thread(target = self.autotweet)
                self._tweet_thread.daemon = True
                self._tweet_thread.name = 'tweet'
                self._tweet_thread.start()

                Utility.log('thread_monnitor', 'Restarted tweet thread')

        if self._examine_alive:
            if not self._examine_thread.is_alive():
                Utility.log('thread_monitor', 'reply thread dead, reviving ...')

                self._examine_thread = Thread(target = self.autoreply)
                self._examine_thread.daemon = True
                self._examine_thread.name = 'examiner'
                self._examine_thread.start()

                Utility.log('thread_monnitor', 'Restarted examine thread')        



    def _construct_tweet(self, seedword = None, prefix = None, suffix = None):
        max_words = 20
        response = ''
        while response == '' or len(response) > 140:
            model = MarkovModel()
            response = model.generate_text(max_words, seedword = seedword)
            if prefix != None: 
                response = '{0} {1}'.format(prefix, response)
            if suffix != None:
                response = '{0} {1}'.format(response, suffix)
            if len(response) > 140:
                max_words -= 1

        return response

    
    def _examine(self):
        while self._examine_alive:
            time.sleep(5)
            self.thread_monitor()
