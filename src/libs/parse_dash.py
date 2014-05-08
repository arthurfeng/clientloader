# -*- coding: utf-8 -*-
from parse_xml import XML
import re

PARSEXML = XML()

def parse_time(mediaPresentationDuration):

    real_time = 0
    mediaPresentationDuration = mediaPresentationDuration.replace('PT','')
    H = mediaPresentationDuration.find('H')
    M = mediaPresentationDuration.find('M')
    S = mediaPresentationDuration.find('S')
    if H > 0:
        H_time = float(mediaPresentationDuration[:H])
        real_time = real_time + H_time * 3600
    if M > 0:
        M_time = float(mediaPresentationDuration[H+1:M])
        real_time = real_time + M_time * 60
    if S > 0:
        S_time = float(mediaPresentationDuration[M+1:S])
        real_time = real_time + S_time
    return real_time

class ParseDASH():

    DEBUG = 0
    DASHPROFILE = {}        
    MPTS = False
    STREAMNUMBER = 0
    TIMESLEEP = 0
    KEEPPLAY = True

    def __init__(self):

        pass

    def start(self, xmlstring):

        try:
            root = PARSEXML.string_to_xml(xmlstring)
            base_url_node = PARSEXML.get_xmlnode(root, "BaseURL")
            adaptation_set_node = PARSEXML.get_xmlnode(root, "AdaptationSet")
            if self.mpd(root) and self.baseurl(base_url_node) \
                                and self.adaptationset(adaptation_set_node):
                return 0, "Parse Dash Playlist Success", self.parse_dash_url(), self.DASHPROFILE 
            else:
                return 1, "Parse Dash Playlist Failed, Please Check Dash Playlist", [], {}
        except Exception, e:
            return 100, "function-parse_dash-ParseDASH-start: %s" % e

    def mpd(self, node):

        try:
            mpd_xmlns = PARSEXML.get_attrvalue(node,'xmlns')
            mpd_type = PARSEXML.get_attrvalue(node, 'type')
            if mpd_type == "static":
                self.KEEPPLAY = False
            mpd_minBufferTime = PARSEXML.get_attrvalue(node, 'minBufferTime')
            mpd_mediaPresentationDuration = parse_time(PARSEXML.get_attrvalue(node, 
                                                'mediaPresentationDuration'))
            mpd_profiles = PARSEXML.get_attrvalue(node, 'profiles')
            if re.search(r"mp2t", mpd_profiles):
                self.MPTS = True
            self.DASHPROFILE["xmlns"] = mpd_xmlns
            self.DASHPROFILE["type"] = mpd_type
            self.DASHPROFILE["minBufferTime"] = mpd_minBufferTime
            self.DASHPROFILE["mediaPresentationDuration"] = mpd_mediaPresentationDuration
            self.DASHPROFILE["profiles"] = mpd_profiles
            return True
        except Exception, e:
            if self.DEBUG:
                print e
            return False

    def baseurl(self, nodes):

        try:
            base_url = ""
            for node in nodes:
                base_url = PARSEXML.get_nodevalue(nodes[0])
            self.DASHPROFILE["BaseURL"] = base_url
            return True
        except Exception, e:
            if self.DEBUG:
                print e
            return False

    def adaptationset(self, nodes):

        try:
            startwithsap, mimetype, segmentalignment, \
                subsegmentalignment, bitstreamswitching = "", "", "", "", ""
            self.DASHPROFILE["AdaptationSets"] = {}
            for node in nodes:
                startwithsap = PARSEXML.get_attrvalue(node, "startWithSAP")
                mimetype = PARSEXML.get_attrvalue(node, "mimeType")
                segmentalignment = PARSEXML.get_attrvalue(node, "segmentAlignment")
                subsegmentalignment = PARSEXML.get_attrvalue(node, "subsegmentAlignment")
                bitstreamswitching = PARSEXML.get_attrvalue(node, "bitstreamSwitching")
                self.DASHPROFILE["AdaptationSets"][mimetype] = {
                                                "mimetype": mimetype,
                                                "startWithSAP": startwithsap,
                                                "segmentAlignment": segmentalignment,
                                                "subsegmentAlignment": subsegmentalignment,
                                                "bitstreamSwitching": bitstreamswitching
                                                }
                self.DASHPROFILE["AdaptationSets"][mimetype].update(self.contentcomponent(PARSEXML.\
                                                                get_xmlnode(node, "ContentComponent")))
                self.DASHPROFILE["AdaptationSets"][mimetype].update(self.representation(PARSEXML.\
                                                                get_xmlnode(node, "Representation")))
                self.DASHPROFILE["AdaptationSets"][mimetype].update(self.segmenttemplate(PARSEXML.\
                                                                get_xmlnode(node, "SegmentTemplate")))
            return True
        except Exception, e:
            if self.DEBUG:
                print e
            return False

    def contentcomponent(self, nodes):

        try:
            content_component_dict = {}
            for node in nodes:
                id = PARSEXML.get_attrvalue(node, "id")
                contenttype = PARSEXML.get_attrvalue(node, "contentType")
                lang = PARSEXML.get_attrvalue(node, "lang")
                content_component_dict[id] = {
                                                        "contentType": contenttype,
                                                        "Lang": lang
                                             }
            return content_component_dict
        except Exception, e:
            if self.DEBUG:
                print e
            return {}

    def representation(self, nodes):

        try:
            representation_dict = {}
            for node in nodes:
                id = PARSEXML.get_attrvalue(node, "id")
                mimeType = PARSEXML.get_attrvalue(node, "mimeType")
                bandwidth = PARSEXML.get_attrvalue(node, "bandwidth")
                startWithSAP = PARSEXML.get_attrvalue(node, "startWithSAP")
                codecs = PARSEXML.get_attrvalue(node, "codecs")
                width = PARSEXML.get_attrvalue(node, "width")
                height = PARSEXML.get_attrvalue(node, "height")
                frameRate = PARSEXML.get_attrvalue(node, "frameRate")
                segment_list_dict = self.segmentlist(PARSEXML.get_xmlnode(node, "SegmentList"))
                initialization_dict = self.initialization(PARSEXML.get_xmlnode(node, "Initialization"))
                segmenturl_dict = self.segmenturl(PARSEXML.get_xmlnode(node, "SegmentURL"))
                representation_dict[id] = {
                                                "mimeType": mimeType,
                                                "bandwidth": int(bandwidth),
                                                "startWithSAP": startWithSAP,
                                                "codecs": codecs,
                                                "width": width,
                                                "height": height,
                                                "frameRate": frameRate
                                                }
                representation_dict[id].update(segment_list_dict)
                representation_dict[id].update(initialization_dict)
                representation_dict[id].update(segmenturl_dict)
            return {"RepresentationIDs": representation_dict}
        except Exception, e:
            if self.DEBUG:
                print e
            return {}

    def segmentlist(self, nodes):

        try:
            timescale = ""
            duration = ""
            startnumber = ""
            for node in nodes:
                timescale = PARSEXML.get_attrvalue(node, "timescale")
                duration = float(PARSEXML.get_attrvalue(node, "duration"))
                startnumber = PARSEXML.get_attrvalue(node, "startNumber")
            if not self.MPTS:
                    duration = float(duration/1000)
            self.TIMESLEEP = duration
            return {"timescale": timescale, "duration": float(duration), 
                        "startNumber": int(startnumber)}
        except Exception, e:
            if self.DEBUG:
                print e
            return {}

    def initialization(self, nodes):

        try:
            sourceurl = ""
            for node in nodes:
                sourceurl = PARSEXML.get_attrvalue(node, "sourceURL")
            return {"sourceURL": sourceurl}
        except Exception, e:
            if self.DEBUG:
                print e
            return {}

    def segmenturl(self, nodes):

        try:
            segmenturl_dict = {}
            count = 1
            for node in nodes:
                media = PARSEXML.get_attrvalue(node, "media")
                segmenturl_dict[count] = media
                count += 1
            return {"SegmentURL": segmenturl_dict}
        except Exception, e:
            if self.DEBUG:
                print e
            return {}
    
    def segmenttemplate(self, nodes):
        
        try:
            if not nodes:
                return {}
            media = ""
            start = ""
            duration = ""
            startnumber = ""
            for node in nodes:
                media = PARSEXML.get_attrvalue(node, "media")
                start = PARSEXML.get_attrvalue(node, "start")
                duration = int(PARSEXML.get_attrvalue(node, "duration"))
                startnumber = PARSEXML.get_attrvalue(node, "startNumber")
                if not self.MPTS:
                    duration = float(duration/1000)
            self.TIMESLEEP = duration
            return {"SegmentTemplate": 
                                {
                        "media": media,
                        "start": start,
                        "duration": float(duration),
                        "startNumber": int(startnumber)
                                }
                        }
        except Exception, e:
            if self.DEBUG:
                print e
            return {}

    def parse_dash_url(self):

        try:
            url_list = list()
            base_url = self.DASHPROFILE["BaseURL"]
            adaptationset_list = self.DASHPROFILE["AdaptationSets"].keys()
            for adaptationset in adaptationset_list:
                representation_id_list =  self.DASHPROFILE["AdaptationSets"][adaptationset]\
                                                        ["RepresentationIDs"].keys()
                if self.DASHPROFILE["AdaptationSets"][adaptationset].get("SegmentTemplate", None):
                    temple_url = self.DASHPROFILE["AdaptationSets"][adaptationset]\
                                                        ["SegmentTemplate"]["media"]
                    for rid in representation_id_list:
                        sub_url_list = list()
                        start_number = self.DASHPROFILE["AdaptationSets"][adaptationset]\
                                                        ["SegmentTemplate"].get("startNumber", 1)
                        seg_duration = self.DASHPROFILE["AdaptationSets"][adaptationset]\
                                                        ["SegmentTemplate"].get("duration", 10)
                        media_duration = self.DASHPROFILE["mediaPresentationDuration"]
                        while media_duration > 0:
                            url = re.sub(r"\$RepresentationID\$", rid, temple_url)
                            url = re.sub(r"\$Number\$", str(start_number), url)
                            url = "%s%s" % (base_url, url)
                            start_number += 1
                            media_duration -= seg_duration
                            sub_url_list.append(url)
                        self.DASHPROFILE["AdaptationSets"][adaptationset]\
                                                ["RepresentationIDs"][rid]\
                                                ["SegmentNumber"] = len(sub_url_list)
                        self.STREAMNUMBER += 1
                        url_list.append(sub_url_list)
                else:
                    for rid in representation_id_list:
                        sub_url_list = self.DASHPROFILE["AdaptationSets"][adaptationset]\
                                                ["RepresentationIDs"][rid]["SegmentURL"].values()
                        self.STREAMNUMBER += 1
                        url_list.append(["%s%s" % (base_url, i) for i in sub_url_list])
                        self.DASHPROFILE["AdaptationSets"][adaptationset]\
                                                ["RepresentationIDs"][rid]\
                                                ["SegmentNumber"] = len(sub_url_list)
                self.DASHPROFILE["StreamNumber"] = self.STREAMNUMBER
            return url_list
        except Exception, e:
            if self.DEBUG:
                print e
            return []
 
if __name__ == "__main__":

    import sys
    import parse_url
    PU = parse_url.ParseUrl() 
    f = open(sys.argv[1],'r')
    lines = f.read()
    f.close()
    PDASH = ParseDASH()
    #PDASH.DEBUG = 1
    #print PDASH.start(lines)[2]
    print PU.get_segment_number("mpts", 0, PDASH.start(lines)[2][0])
