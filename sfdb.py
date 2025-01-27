#-------------------------------------------------------------------------------
# Name:         sfdb
# Purpose:      Common functions for working with the database back-end.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     15/05/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import hashlib
import random
import sqlite3
import sys
import time
from sflib import SpiderFoot

# SpiderFoot class passed to us
sf = None

class SpiderFootDb:
    # Queries for creating the SpiderFoot database
    createQueries = [
            "PRAGMA journal_mode=WAL",
            "CREATE TABLE tbl_event_types ( \
                event       VARCHAR NOT NULL PRIMARY KEY, \
                event_descr VARCHAR NOT NULL, \
                event_raw   INT NOT NULL DEFAULT 0 \
            )",
            "CREATE TABLE tbl_config ( \
                scope   VARCHAR NOT NULL, \
                opt     VARCHAR NOT NULL, \
                val     VARCHAR NOT NULL, \
                PRIMARY KEY (scope, opt) \
            )",
            "CREATE TABLE tbl_scan_instance ( \
                guid        VARCHAR NOT NULL PRIMARY KEY, \
                name        VARCHAR NOT NULL, \
                seed_target VARCHAR NOT NULL, \
                created     INT DEFAULT 0, \
                started     INT DEFAULT 0, \
                ended       INT DEFAULT 0, \
                status      VARCHAR NOT NULL \
            )",
            "CREATE TABLE tbl_scan_log ( \
                scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid), \
                generated           INT NOT NULL, \
                component           VARCHAR, \
                type                VARCHAR NOT NULL, \
                message             VARCHAR \
            )",
            "CREATE TABLE tbl_scan_config ( \
                scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid), \
                component           VARCHAR NOT NULL, \
                opt                 VARCHAR NOT NULL, \
                val                 VARCHAR NOT NULL \
            )",
            "CREATE TABLE tbl_scan_results ( \
                scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid), \
                hash                VARCHAR NOT NULL, \
                type                VARCHAR NOT NULL REFERENCES tbl_event_types(event), \
                generated           INT NOT NULL, \
                confidence          INT NOT NULL DEFAULT 100, \
                visibility          INT NOT NULL DEFAULT 100, \
                risk                INT NOT NULL DEFAULT 0, \
                module              VARCHAR NOT NULL, \
                data                VARCHAR, \
                source_event_hash  VARCHAR DEFAULT 'ROOT' \
            )",
            "CREATE INDEX idx_scan_results_id ON tbl_scan_results (scan_instance_id)",
            "CREATE INDEX idx_scan_results_type ON tbl_scan_results (scan_instance_id, type)",
            "CREATE INDEX idx_scan_results_hash ON tbl_scan_results (scan_instance_id, hash)",
            "CREATE INDEX idx_scan_results_srchash ON tbl_scan_results (scan_instance_id, source_event_hash)",
            "CREATE INDEX idx_scan_logs ON tbl_scan_log (scan_instance_id)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE', 'Affiliate - Hostname', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE_DOMAIN', 'Affiliate - Domain', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE_IPADDR', 'Affiliate - IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE_IP_SUBNET', 'Affiliate - IP Address - Subnet', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE_WEB_CONTENT', 'Affiliate - Web Content', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('BGP_AS', 'BGP AS Ownership', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('BLACKLISTED_IPADDR', 'Blacklisted IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('BLACKLISTED_AFFILIATE_IPADDR', 'Blacklisted Affiliate IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('CO_HOSTED_SITE', 'Co-Hosted Site', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED', 'Defaced', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED_IPADDR', 'Defaced IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED_AFFILIATE', 'Defaced Affiliate', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED_AFFILIATE_IPADDR', 'Defaced Affiliate IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED_COHOST', 'Defaced Co-Hosted Site', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEVICE_TYPE', 'Device Type', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DOMAIN_NAME', 'Domain Name', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('EMAILADDR', 'Email Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('GEOINFO', 'Physical Location', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('HTTP_CODE', 'HTTP Status Code', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('HUMAN_NAME', 'Human Name', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('INITIAL_TARGET', 'User-Supplied Target', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('INTERESTING_FILE', 'Interesting File', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('IP_ADDRESS', 'IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('IP_SUBNET', 'IP Address - Subnet', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('NETBLOCK', 'Netblock Ownership', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_ASN', 'Malicious AS', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_IPADDR', 'Malicious IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_COHOST', 'Malicious Co-Hosted Site', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_DOMAIN_NAME', 'Malicious Domain Name', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_SUBDOMAIN', 'Malicious Sub-domain/Host', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_AFFILIATE', 'Malicious Affiliate', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_AFFILIATE_IPADDR', 'Malicious Affiliate IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_NETBLOCK', 'Owned Netblock with Malicious IP', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_SUBNET', 'Malicious IP on Same Subnet', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('LINKED_URL_INTERNAL', 'Linked URL - Internal', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('LINKED_URL_EXTERNAL', 'Linked URL - External', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('OPERATING_SYSTEM', 'Operating System', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PASTEBIN_CONTENT', 'PasteBin Content', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PROVIDER_DNS', 'Name Server (DNS ''NS'' Records)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PROVIDER_INTERNET', 'Internet Service Provider', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PROVIDER_MAIL', 'Email Gateway (DNS ''MX'' Records)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PROVIDER_JAVASCRIPT', 'Externally Hosted Javascript', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('RAW_RIR_DATA', 'Raw Data from RIRs', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('RAW_DNS_RECORDS', 'Raw DNS Records', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('RAW_FILE_META_DATA', 'Raw File Meta Data', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SEARCH_ENGINE_WEB_CONTENT', 'Search Engine''s Web Content', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SOCIAL_MEDIA', 'Social Media Presence', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SUBDOMAIN', 'Sub-domain/Hostname', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SIMILARDOMAIN', 'Similar Domain', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_ISSUED', 'SSL Certificate - Issued to', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_ISSUER', 'SSL Certificate - Issued by', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_MISMATCH', 'SSL Certificate Host Mismatch', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_EXPIRED', 'SSL Certificate Expired', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_EXPIRING', 'SSL Certificate Expiring', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_RAW', 'SSL Certificate - Raw Data', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('TARGET_WEB_CONTENT', 'Web Content', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('TARGET_WEB_COOKIE', 'Cookies', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('TCP_PORT_OPEN', 'Open TCP Port', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('TCP_PORT_OPEN_BANNER', 'Open TCP Port Banner', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_FORM', 'URL (Form)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_FLASH', 'URL (Uses Flash)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_JAVASCRIPT', 'URL (Uses Javascript)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_WEB_FRAMEWORK', 'URL (Uses a Web Framework)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_JAVA_APPLET', 'URL (Uses Java applet)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_STATIC', 'URL (Purely Static)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_PASSWORD', 'URL (Accepts Passwords)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_UPLOAD', 'URL (Accepts Uploads)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('WEBSERVER_BANNER', 'Web Server', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('WEBSERVER_HTTPHEADERS', 'HTTP Headers', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('WEBSERVER_STRANGEHEADER', 'Non-Standard HTTP Header', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('WEBSERVER_TECHNOLOGY', 'Web Technology', 0)"
    ]

    def __init__(self, opts):
        global sf
        sf = SpiderFoot(opts)

        # connect() will create the database file if it doesn't exist, but
        # at least we can use this opportunity to ensure we have permissions to
        # read and write to such a file.
        dbh = sqlite3.connect(sf.myPath() + "/" + opts['__database'], timeout=10)
        if dbh == None:
            sf.fatal("Could not connect to internal database, and couldn't create " + \
                opts['__database'])
        dbh.text_factory = str

        self.conn = dbh
        self.dbh = dbh.cursor()

        # Now we actually check to ensure the database file has the schema set
        # up correctly.
        try:
            self.dbh.execute('SELECT COUNT(*) FROM tbl_scan_config')
        except sqlite3.Error:
            # .. If not set up, we set it up.
            try:
                self.create()
            except BaseException as e:
                sf.error("Tried to set up the SpiderFoot database schema, but failed: " + \
                    e.args[0])
        return

    #
    # Back-end database operations
    #

    # Create the back-end schema
    def create(self):
        try:
            for qry in self.createQueries:
                self.dbh.execute(qry)
            self.conn.commit()
        except sqlite3.Error as e:
            raise BaseException("SQL error encountered when setting up database: " +
                e.args[0])

    # Close the database handle
    def close(self):
        self.dbh.close()

    # Get event types
    def eventTypes(self):
        qry = "SELECT event_descr, event, event_raw FROM tbl_event_types"
        try:
            self.dbh.execute(qry)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when retreiving event types:" +
                e.args[0])

    # Log an event to the database
    def scanLogEvent(self, instanceId, classification, message, component=None):
        if component == None:
            component = "SpiderFoot"

        qry = "INSERT INTO tbl_scan_log \
            (scan_instance_id, generated, component, type, message) \
            VALUES (?, ?, ?, ?, ?)"
        try:
            self.dbh.execute(qry, (
                    instanceId, time.time() * 1000, component, classification, message
                ))
            self.conn.commit()
        except sqlite3.Error as e:
            if "locked" in e.args[0]:
                # TODO: Do something smarter here to handle locked databases
                sf.fatal("Unable to log event in DB: " + e.args[0])
            else:
                sf.fatal("Unable to log event in DB: " + e.args[0])

        return True

    # Generate an globally unique ID for this scan
    def scanInstanceGenGUID(self, scanName):
        hashStr = hashlib.sha256(
                scanName +
                str(time.time() * 1000) +
                str(random.randint(100000, 999999))
            ).hexdigest()
        return hashStr

    # Store a scan instance
    def scanInstanceCreate(self, instanceId, scanName, scanTarget):
        qry = "INSERT INTO tbl_scan_instance \
            (guid, name, seed_target, created, status) \
            VALUES (?, ?, ?, ?, ?)"
        try:
            self.dbh.execute(qry, (
                    instanceId, scanName, scanTarget, time.time() * 1000, 'CREATED'
                ))
            self.conn.commit()
        except sqlite3.Error as e:
            sf.fatal("Unable to create instance in DB: " + e.args[0])

        return True

    # Update the start time, end time or status (or all 3) of a scan instance
    def scanInstanceSet(self, instanceId, started=None, ended=None, status=None):
        qvars = list()
        qry = "UPDATE tbl_scan_instance SET "

        if started != None:
            qry += " started = ?,"
            qvars.append(started)

        if ended != None:
            qry += " ended = ?,"
            qvars.append(ended)

        if status != None:
            qry += " status = ?,"
            qvars.append(status)

        # guid = guid is a little hack to avoid messing with , placement above
        qry += " guid = guid WHERE guid = ?"
        qvars.append(instanceId)

        try:
            self.dbh.execute(qry, qvars)
            self.conn.commit()
        except sqlite3.Error:
            sf.fatal("Unable to set information for the scan instance.")

    # Return info about a scan instance (name, target, created, started,
    # ended, status) - don't need this yet - untested
    def scanInstanceGet(self, instanceId):
        qry = "SELECT name, seed_target, ROUND(created/1000) AS created, \
            ROUND(started/1000) AS started, ROUND(ended/1000) AS ended, status \
            FROM tbl_scan_instance WHERE guid = ?"
        qvars = [instanceId]
        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchone()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when retreiving scan instance:" +
                e.args[0])

    # Obtain a summary of the results per event type
    def scanResultSummary(self, instanceId):
        qry = "SELECT r.type, e.event_descr, MAX(ROUND(generated)) AS last_in, \
            count(*) AS total, count(DISTINCT r.data) as utotal FROM \
            tbl_scan_results r, tbl_event_types e WHERE e.event = r.type \
            AND r.scan_instance_id = ? GROUP BY r.type ORDER BY e.event_descr"
        qvars = [instanceId]
        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching result summary: " +
                e.args[0])

    # Obtain the data for a scan and event type
    def scanResultEvent(self, instanceId, eventType='ALL'):
        qry = "SELECT ROUND(c.generated) AS generated, c.data, \
            s.data as 'source_data', \
            c.module, c.type, c.confidence, c.visibility, c.risk, c.hash, \
            c.source_event_hash, t.event_descr \
            FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t \
            WHERE c.scan_instance_id = ? AND c.source_event_hash = s.hash AND \
            s.scan_instance_id = c.scan_instance_id AND \
            t.event = c.type"

        qvars = [instanceId]

        if eventType != "ALL":
            qry = qry + " AND c.type = ?"
            qvars.append(eventType)

        qry = qry + " ORDER BY c.data"

        #print "QRY: " + qry

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching result events: " +
                e.args[0])

    # Obtain a unique list of elements
    def scanResultEventUnique(self, instanceId, eventType='ALL'):
        qry = "SELECT DISTINCT data, type, COUNT(*) FROM tbl_scan_results \
            WHERE scan_instance_id = ?"
        qvars = [instanceId]

        if eventType != "ALL":
            qry = qry + " AND type = ?"
            qvars.append(eventType)

        qry = qry + " GROUP BY type, data ORDER BY COUNT(*)"

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching unique result events: " +
                e.args[0])

    # Get scan logs
    def scanLogs(self, instanceId, limit=None):
        qry = "SELECT generated AS generated, component, \
            type, message FROM tbl_scan_log WHERE scan_instance_id = ? \
            ORDER BY generated DESC"
        qvars = [instanceId]

        if limit != None:
            qry = qry + " LIMIT ?"
            qvars.append(limit)

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching scan logs: " +
                e.args[0])

    # Get scan errors
    def scanErrors(self, instanceId, limit=None):
        qry = "SELECT generated AS generated, component, \
            message FROM tbl_scan_log WHERE scan_instance_id = ? \
            AND type = 'ERROR' ORDER BY generated DESC"
        qvars = [instanceId]

        if limit != None:
            qry = qry + " LIMIT ?"
            qvars.append(limit)

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching scan errors: " +
                e.args[0])

    # Delete a scan instance
    def scanInstanceDelete(self, instanceId):
        qry1 = "DELETE FROM tbl_scan_instance WHERE guid = ?"
        qry2 = "DELETE FROM tbl_scan_config WHERE scan_instance_id = ?"
        qry3 = "DELETE FROM tbl_scan_results WHERE scan_instance_id = ?"
        qry4 = "DELETE FROM tbl_scan_log WHERE scan_instance_id = ?"
        qvars = [instanceId]
        try:
            self.dbh.execute(qry1, qvars)
            self.dbh.execute(qry2, qvars)
            self.dbh.execute(qry3, qvars)
            self.dbh.execute(qry4, qvars)
            self.conn.commit()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when deleting scan: " +
                e.args[0])

    # Store the default configuration
    def configSet(self, optMap=dict()):
        qry = "REPLACE INTO tbl_config (scope, opt, val) VALUES (?, ?, ?)"
        for opt in optMap.keys():
            # Module option
            if ":" in opt:
                parts = opt.split(':')
                qvals = [ parts[0], parts[1], optMap[opt] ]
            else:
            # Global option
                qvals = [ "GLOBAL", opt, optMap[opt] ]

            try:
                self.dbh.execute(qry, qvals)
            except sqlite3.Error as e:
                sf.error("SQL error encountered when storing config, aborting: " +
                    e.args[0])

            self.conn.commit()

    # Retreive the config from the database
    def configGet(self):
        qry = "SELECT scope, opt, val FROM tbl_config"
        try:
            retval = dict()
            self.dbh.execute(qry)
            for [scope, opt, val] in self.dbh.fetchall():
                if scope == "GLOBAL":
                    retval[opt] = val
                else:
                    retval[scope + ":" + opt] = val

            return retval
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching configuration: " + e.args[0])

    # Reset the config to default (clear it from the DB and let the hard-coded
    # settings in the code take effect.)
    def configClear(self):
        qry = "DELETE from tbl_config"
        try:
            self.dbh.execute(qry)
            self.conn.commit()
        except sqlite3.Error as e:
            sf.error("Unable to clear configuration from the database: " + e.args[0])

    # Store a configuration value for a scan
    def scanConfigSet(self, id, optMap=dict()):
        qry = "REPLACE INTO tbl_scan_config \
                (scan_instance_id, component, opt, val) VALUES (?, ?, ?, ?)"

        for opt in optMap.keys():
            # Module option
            if ":" in opt:
                parts = opt.split(':')
                qvals = [ id, parts[0], parts[1], optMap[opt] ]
            else:
            # Global option
                qvals = [ id, "GLOBAL", opt, optMap[opt] ]

            try:
                self.dbh.execute(qry, qvals)
            except sqlite3.Error as e:
                sf.error("SQL error encountered when storing config, aborting: " +
                    e.args[0])

            self.conn.commit()

    # Retreive configuration data for a scan component
    def scanConfigGet(self, instanceId):
        qry = "SELECT component, opt, val FROM tbl_scan_config \
                WHERE scan_instance_id = ? ORDER BY component, opt"
        qvars = [instanceId]
        try:
            retval = dict()
            self.dbh.execute(qry, qvars)
            for [component, opt, val] in self.dbh.fetchall():
                if component == "GLOBAL":
                    retval[opt] = val
                else:
                    retval[component + ":" + opt] = val
            return retval
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching configuration: " + e.args[0])

    # Store an event
    # eventData is a SpiderFootEvent object with the following variables:
    # - eventType: the event, e.g. URL_FORM, RAW_DATA, etc.
    # - generated: time the event occurred
    # - confidence: how sure are we of this data's validity, 0-100
    # - visibility: how 'visible' was this data, 0-100
    # - risk: how much risk does this data represent, 0-100
    # - module: module that generated the event
    # - data: the actual data, i.e. a URL, port number, webpage content, etc.
    # - sourceEventHash: hash of the event that triggered this event
    # And getHash() will return the event hash.
    def scanEventStore(self, instanceId, sfEvent, truncateSize=0):
        storeData = ''

        if type(sfEvent.data) is not unicode:
            # If sfEvent.data is a dict or list, convert it to a string first, as
            # those types do not have a unicode converter.
            if type(sfEvent.data) is str:
                storeData = unicode(sfEvent.data, 'utf-8', errors='replace')
            else:
                try:
                    storeData = unicode(str(sfEvent.data), 'utf-8', errors='replace')
                except BaseException as e:
                    sf.fatal("Unhandled type detected: " + str(type(sfEvent.data)))
        else:
            storeData = sfEvent.data

        if truncateSize > 0:
            storeData = storeData[0:truncateSize]

        qry = "INSERT INTO tbl_scan_results \
            (scan_instance_id, hash, type, generated, confidence, \
            visibility, risk, module, data, source_event_hash) \
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        qvals = [ instanceId, sfEvent.getHash(), sfEvent.eventType, sfEvent.generated,
            sfEvent.confidence, sfEvent.visibility, sfEvent.risk,
            sfEvent.module, storeData, sfEvent.sourceEventHash ]

        #print "STORING: " + str(qvals)

        try:
            self.dbh.execute(qry, qvals)
            self.conn.commit()
            return None
        except sqlite3.Error as e:
            sf.fatal("SQL error encountered when storing event data (" + str(self.dbh) + ": " +
                e.args[0])

    # List of all previously run scans
    def scanInstanceList(self):
        # SQLite doesn't support OUTER JOINs, so we need a work-around that
        # does a UNION of scans with results and scans without results to 
        # get a complete listing.
        qry = "SELECT i.guid, i.name, i.seed_target, ROUND(i.created/1000), \
            ROUND(i.started)/1000 as started, ROUND(i.ended)/1000, i.status, COUNT(r.type) \
            FROM tbl_scan_instance i, tbl_scan_results r WHERE i.guid = r.scan_instance_id \
            GROUP BY i.guid \
            UNION ALL \
            SELECT i.guid, i.name, i.seed_target, ROUND(i.created/1000), \
            ROUND(i.started)/1000 as started, ROUND(i.ended)/1000, i.status, '0' \
            FROM tbl_scan_instance i  WHERE i.guid NOT IN ( \
            SELECT distinct scan_instance_id FROM tbl_scan_results) \
            ORDER BY started DESC"
        try:
            self.dbh.execute(qry)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching scan list: " + e.args[0])

    # History of data from the scan
    def scanResultHistory(self, instanceId):
        qry = "SELECT STRFTIME('%H:%M %w', generated, 'unixepoch') AS hourmin, \
                type, COUNT(*) FROM tbl_scan_results \
                WHERE scan_instance_id = ? GROUP BY hourmin, type"
        qvars = [instanceId]
        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching scan history: " + e.args[0])


    # Get the source IDs, types and data for a set of IDs
    def scanElementSources(self, instanceId, elementIdList):
        # the output of this needs to be aligned with scanResultEvent,
        # as other functions call both expecting the same output.
        qry = "SELECT ROUND(c.generated) AS generated, c.data, \
            s.data as 'source_data', \
            c.module, c.type, c.confidence, c.visibility, c.risk, c.hash, \
            c.source_event_hash, t.event_descr \
            FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t \
            WHERE c.scan_instance_id = ? AND c.source_event_hash = s.hash AND \
            s.scan_instance_id = c.scan_instance_id AND \
            t.event = c.type AND c.hash in ("
        qvars = [instanceId]

        for hashId in elementIdList:
            qry = qry + "'" + hashId + "',"
        qry = qry + "'')"

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when getting source element IDs: " + e.args[0])


