#-------------------------------------------------------------------------------
# Name:         sfp_socialprofiles
# Purpose:      Obtains social media profiles of any identified human names.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     12/04/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
import urllib
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

sites = {
    # Search string to use, domain name the profile will sit on within 
    # those search results.
    "Facebook": ['+intitle:%22{0}%22%20+site:facebook.com', 
        '"(https?://[a-z\.]*facebook.[a-z\.]+/[^\"<> ]+)"' ],
    "Google+": ['+intitle:%22{0}%22%20+site:plus.google.com', 
        '"(https?://plus.google.[a-z\.]+/\d+[^\"<>\/ ]+)"' ],
    "LinkedIn": ['+intitle:%22{0}%22%20+site:linkedin.com', 
        '"(https?://[a-z\.]*linkedin.[a-z\.]+/[^\"<> ]+)"' ]
}

class sfp_socialprofiles(SpiderFootPlugin):
    """Social Media Profiles:Identify the social media profiles for human names identified."""

    # Default options
    opts = {
        'pages': 1,
        'method': "yahoo",
        'tighten': True
    }

    # Option descriptions
    optdescs = {
        'pages': "Number of search engine pages of identified profiles to iterate through.",
        'tighten': "Tighten results by expecting to find the keyword of the target domain mentioned in the social media profile page results?",
        'method': "Search engine to use: google, yahoo or bing."
    }

    # Target
    baseDomain = None
    keyword = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

        self.keyword = sf.domainKeyword(self.baseDomain, 
            self.opts['_internettlds']).lower()

    # What events is this module interested in for input
    def watchedEvents(self):
        return [ "HUMAN_NAME" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "SOCIAL_MEDIA" ]

    def yahooCleaner(self, string):
        ret = "\"" + urllib.unquote(string.group(1)) + "\""
        return ret

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        self.currentEventSrc = event

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # Don't look up stuff twice
        if eventData in self.results:
            sf.debug("Skipping " + eventData + " as already mapped.")
            return None
        else:
            self.results.append(eventData)

        for site in sites.keys():
            searchStr = sites[site][0].format(eventData).replace(" ", "%20")
            searchDom = sites[site][1]

            if self.opts['method'].lower() == "google":
                results = sf.googleIterate(searchStr, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'], 
                    timeout=self.opts['_fetchtimeout']))

            if self.opts['method'].lower() == "yahoo":
                results = sf.yahooIterate(searchStr, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'], 
                    timeout=self.opts['_fetchtimeout']))

            if self.opts['method'].lower() == "bing":
                results = sf.bingIterate(searchStr, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'],
                    timeout=self.opts['_fetchtimeout']))

            if results == None:
                sf.info("No data returned from " + self.opts['method'] + ".")
                return None

            if self.checkForStop():
                return None

            pauseSecs = random.randint(4, 15)
            sf.debug("Pausing for " + str(pauseSecs))
            time.sleep(pauseSecs)

            for key in results.keys():
                instances = list()
                # Yahoo requires some additional parsing
                if self.opts['method'].lower() == "yahoo":
                    res = re.sub("RU=(.[^\/]+)\/RK=", self.yahooCleaner, 
                        results[key], 0)
                else:
                    res = results[key]

                matches = re.findall(searchDom, res, re.IGNORECASE)

                if matches != None:
                    for match in matches:
                        if match in instances:
                            continue
                        else:
                            instances.append(match)

                        if self.checkForStop():
                            return None

                        # Fetch the profile page if we are checking
                        # for a firm relationship.
                        if self.opts['tighten']:
                            pres = sf.fetchUrl(match, timeout=self.opts['_fetchtimeout'],
                                useragent=self.opts['_useragent'])

                            if pres['content'] == None:
                                continue
                            else:
                                if re.search("[^a-zA-Z\-\_]" + self.keyword + \
                                    "[^a-zA-Z\-\_]", pres['content'], re.IGNORECASE) == None:
                                    continue

                        sf.info("Social Media Profile found at " + site + ": " + match)
                        evt = SpiderFootEvent("SOCIAL_MEDIA", match, 
                            self.__name__, event)
                        self.notifyListeners(evt)

                # Submit the bing results for analysis
                evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT", res, 
                    self.__name__, event)
                self.notifyListeners(evt)

# End of sfp_socialprofiles class
