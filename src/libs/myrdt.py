# -*- coding: utf-8 -*-
# RTP Datagram Module
import struct
import StringIO
from parse_sdp import Sdpplin

class rmff_fileheader_t:
    object_id = '.RMF'
    size = 18
    object_version = 0
    file_version = 0

    def getSize(self):
        return self.size

    def __init__(self, num_headers):
        self.num_headers = num_headers

    def dump(self):
        d = []
        d.append(self.object_id)
        d.append(struct.pack('!I', self.size))
        d.append(struct.pack('!H', self.object_version))
        d.append(struct.pack('!I', self.file_version))
        d.append(struct.pack('!I', self.num_headers))
        return ''.join(d)

    def __str__(self):
        return self.dump()

class rmff_prop_t:
    object_id = 'PROP'
    size = 50
    object_version = 0

    def getSize(self):
        return self.size

    def __init__(self, max_bit_rate, avg_bit_rate, max_packet_size,
                 avg_packet_size, num_packets, duration, preroll, index_offset,
                 data_offset, num_streams, flags):
        self.max_bit_rate = max_bit_rate
        self.avg_bit_rate = avg_bit_rate
        self.max_packet_size = max_packet_size
        self.avg_packet_size = avg_packet_size
        self.num_packets = num_packets
        self.duration = duration
        self.preroll = preroll
        self.index_offset = index_offset
        self.data_offset = data_offset
        self.num_streams = num_streams
        self.flags = flags

    def dump(self):
        d = []
        d.append(self.object_id)
        d.append(struct.pack('!I', self.size))
        d.append(struct.pack('!H', self.object_version))
        d.append(struct.pack('!I', self.max_bit_rate))
        d.append(struct.pack('!I', self.avg_bit_rate))
        d.append(struct.pack('!I', self.max_packet_size))
        d.append(struct.pack('!I', self.avg_packet_size))
        d.append(struct.pack('!I', self.num_packets))
        d.append(struct.pack('!I', self.duration))
        d.append(struct.pack('!I', self.preroll))
        d.append(struct.pack('!I', self.index_offset))
        d.append(struct.pack('!I', self.data_offset))
        d.append(struct.pack('!H', self.num_streams))
        d.append(struct.pack('!H', self.flags))
        return ''.join(d)

    def __str__(self):
        return self.dump()

class rmff_mdpr_t:
    object_id = 'MDPR'
    object_version = 0

    def __init__(self, stream_number, max_bit_rate, avg_bit_rate,
                 max_packet_size, avg_packet_size, start_time, preroll,
                 duration, stream_name, mime_type, type_specific_data):
        self.stream_number = stream_number
        self.max_bit_rate = max_bit_rate
        self.avg_bit_rate = avg_bit_rate
        self.max_packet_size = max_packet_size
        self.avg_packet_size = avg_packet_size
        self.start_time = start_time
        self.preroll = preroll
        self.duration = duration
        self.stream_name = stream_name
        self.mime_type = mime_type
        self.type_specific_data = type_specific_data

    def getSize(self):
        size = 46
        size += len(self.stream_name)
        size += len(self.mime_type)
        size += len(self.type_specific_data)
        return size        

    def dump(self):
        d = []
        d.append(self.object_id)
        d.append(struct.pack('!I', self.getSize()))
        d.append(struct.pack('!H', self.object_version))
        d.append(struct.pack('!H', self.stream_number))
        d.append(struct.pack('!I', self.max_bit_rate))
        d.append(struct.pack('!I', self.avg_bit_rate))
        d.append(struct.pack('!I', self.max_packet_size))
        d.append(struct.pack('!I', self.avg_packet_size))
        d.append(struct.pack('!I', self.start_time))
        d.append(struct.pack('!I', self.preroll))
        d.append(struct.pack('!I', self.duration))
        d.append(struct.pack('B', len(self.stream_name)))
        d.append(self.stream_name)
        d.append(struct.pack('B', len(self.mime_type)))
        d.append(self.mime_type)
        d.append(struct.pack('!I', len(self.type_specific_data)))
        d.append(self.type_specific_data)
        return ''.join(d)

    def __str__(self):
        return self.dump()
        

class rmff_cont_t:
    object_id = 'CONT'
    object_version = 0

    def __init__(self, title, author, copyright, comment):
        self.title = title
        self.author = author
        self.copyright = copyright
        self.comment = comment

    def getSize(self):
        return len(self.title) + len(self.author) + len(self.copyright) + len(self.comment) + 18

    def dump(self):
        d = []
        d.append(self.object_id)
        d.append(struct.pack('!I', self.getSize()))
        d.append(struct.pack('!H', self.object_version))
        for field in [self.title, self.author, self.copyright, self.comment]:
            d.append(struct.pack('!H', len(field)))
            d.append(field)
        return ''.join(d)

    def __str__(self):
        return self.dump()

class rmff_data_t:
    object_id = 'DATA'
    size = 18
    object_version = 0

    def getSize(self):
        return self.size

    def __init__(self, num_packets, next_data_header):
        self.num_packets = num_packets
        self.next_data_header = next_data_header

    def dump(self):
        d = []
        d.append(self.object_id)
        d.append(struct.pack('!I', self.size))
        d.append(struct.pack('!H', self.object_version))
        d.append(struct.pack('!I', self.num_packets))
        d.append(struct.pack('!I', self.next_data_header))
        return ''.join(d)

    def __str__(self):
        return self.dump()

class rmff_header_t:
    def __init__(self):
        self.fileheader = None
        self.prop = None
        self.streams = []
        self.cont = None
        self.data = None

    def dump(self):
        # Recomputes the data offset
        self.prop.data_offset = self.fileheader.getSize() + self.prop.getSize() + self.cont.getSize() + sum(s.getSize() for s in self.streams)
        d = []
        d.append(self.fileheader.dump())
        d.append(self.prop.dump())
        d.append(self.cont.dump())
        for s in self.streams:
            d.append(s.dump())
        d.append(self.data.dump())
        return ''.join(d)

class rmff_pheader_t:
    """ The contents of this class get inserted
    between RDT data in the output file """
    object_version = 0
    length = None
    stream_number = 0
    timestamp = None
    reserved = 0
    flags = 0

    def dump(self):
        d = []
        d.append(struct.pack('!H', self.object_version))
        d.append(struct.pack('!H', self.length))
        d.append(struct.pack('!H', self.stream_number))
        d.append(struct.pack('!I', self.timestamp))
        d.append(struct.pack('B', self.reserved))
        d.append(struct.pack('B', self.flags))
        return ''.join(d)

    def __str__(self):
        return self.dump()

# Real Assembly Parser
# Copyright (C) 2008 David Bern
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Logging can be enabled in the init method

import logging

class RuleString:
    """ Buffer containing the ASM rule book """
    def __init__(self, string):
        self._str = string
        self.idx = 0
        
    def seek_end(self):
        self.idx = len(self._str)-1

    def eof(self):
        return self.idx >= len(self._str)-1

    def __getitem__(self, key):
        return self._str[self.idx + key]

    def next(self):
        self.idx += 1
        self.sym = self._str[self.idx]
        return self.sym

    def nextChar(self):
        self.next()
        while len(self.sym.strip()) == 0:
            self.next()
        return self.sym

    def isCharElseNext(self):
        if self.sym.strip():
            return self.sym
        else:
            return self.nextChar()

    def dump(self, amount):
        return self._str[self.idx:self.idx + amount]
        

class Asmrp:
    eval_chars = ['<','=','>']
    special_chars = ['$','#',')','(']

    def __init__(self, rules, symbols):
        logger = logging.getLogger('ASMRP')
# Uncomment the following to enable logging
#        logging.basicConfig(level=logging.DEBUG, filename='asmrp.txt')
        
        self.logger = logger
        
        self.rules = rules
        self.logger.debug('Rules: ' + rules)
        self.matches = []
        self.symbols = symbols
        self.special_chars.extend(self.eval_chars)
        self.indent = ''

    def asmrp_find_id(self, rules):
        symbol = ''
        while rules.sym not in self.special_chars:
            symbol += rules.sym
            rules.next()
        symbol = symbol.strip()
        self.logger.debug(self.indent + 'Found symbol: %s => %s' % (symbol, self.symbols[symbol]))
        return self.symbols[symbol]

    def asmrp_operand(self, rules):
        rules.isCharElseNext()
        self.logger.debug(self.indent + 'Finding operand: %s' % rules.sym)
        if rules.sym == '$':
            self.logger.debug(self.indent + 'Found variable symbol')
            rules.next()
            return self.asmrp_find_id(rules)
        elif rules.sym.isdigit():
            self.logger.debug(self.indent + 'Found numerical operand')
            number = ''
            while rules.sym.isdigit():
                number += rules.sym
                rules.next()
            self.logger.debug(self.indent + 'Number: %s' % number)
            return int(number)
        elif rules.sym == '(':
            self.logger.debug(self.indent + 'Open paren')
            rules.nextChar()
            self.indent += ' '
            ret = self.asmrp_condition(rules)
            rules.isCharElseNext()
            self.indent = self.indent[:-1]
            if rules.sym != ')':
                self.logger.debug(self.indent + 'Expected right paren!')
            else:
                self.logger.debug(self.indent + 'Close paren')
            rules.nextChar()
            return ret
        else:
            self.logger.debug('Unknown operand!')
            exit()

    def asmrp_comp_expression(self, rules):
        """ Evaluates an expression such as $Bandwidth > 500 """
        self.logger.debug(self.indent + 'Expression getting a operand')
        self.indent += ' '
        a = self.asmrp_operand(rules)
        self.indent = self.indent[:-1]
        rules.isCharElseNext()
        if rules.sym in [',',';',')','&','|']:
            return a
        operator = rules.sym
        rules.next()
        if rules.sym == '=':
            operator += '='
            rules.nextChar()
        self.logger.debug(self.indent + 'Expression operator: %s' % operator)
        self.logger.debug(self.indent + 'Expression getting b operand')
        self.indent += ' '
        b = self.asmrp_operand(rules)
        self.indent = self.indent[:-1]
        self.logger.debug(self.indent + 'Expression: %s %s %s' % (a,operator,b))
        if operator == '<':
            return a < b
        if operator == '<=':
            return a <= b
        if operator == '==':
            return a == b
        if operator == '>':
            return a > b
        if operator == '>=':
            return a >= b

    def asmrp_condition(self, rules):
        """ Evaluates a condition
        e.g. $Bandwidth > 500 && $Bandwidth < 1000 """
        self.logger.debug(self.indent + 'Condition getting a operand')
        self.indent += ' '
        a = self.asmrp_comp_expression(rules)
        self.indent = self.indent[:-1]
        self.logger.debug(self.indent + 'Condition a: %s' % a)
        while rules.dump(2) in ['&&','||']:
            operator = rules.dump(2)
            self.logger.debug(self.indent + 'Condition Operator: %s' % operator)
            rules.nextChar()
            rules.nextChar()
            b = self.asmrp_comp_expression(rules)
            self.logger.debug(self.indent + 'Condition: %s %s %s' % (a,operator,b))
            if operator == '&&':
                return a and b
            if operator == '||':
                return a or b
        self.logger.debug(self.indent + 'Returning condition: %s' % a)
        return a

    def asmrp_assignment(self, rules):
        self.logger.debug(self.indent + 'Performing assignment')
        name = ''
        while rules.sym != '=':
            name += rules.sym
            rules.next()
        name = name.strip()
        self.logger.debug(self.indent + 'Assignment name: %s' % name)
        rules.nextChar()
        value = rules[0]
        while rules[0] not in [',',';'] and not rules.eof():
            rules.next()
            value += rules.sym
        while ord(value[-1]) < 33 or value[-1] in [',',';']:
            value = value[:-1]
        self.symbols[name] = value
        self.logger.debug(self.indent + 'Assignment [%s] = %s' % (name,value))

    def asmrp_rule(self, rules):
        oper = rules[0]
        self.logger.debug('Next oper: %s' % oper)
        if oper == '#':
            self.logger.debug('# Assignment')
            # Assignment
            rules.nextChar()
            self.indent += ' '
            ret = self.asmrp_condition(rules)
            self.logger.debug('Assignment condition result: %s' % ret)
            if ret:
                while rules[0] == ',' and not rules.eof():
                    rules.nextChar()
                    self.asmrp_assignment(rules)
                if not rules.eof():
                    rules.nextChar()
                return True
            else:
                while rules[0] != ';' and not rules.eof():
                    rules.nextChar()
                if not rules.eof():
                    rules.nextChar()
        else:
            self.logger.debug('Unknown operator: %s' % oper)
            rules.seek_end()
            return False

    def asmrp_eval(self, rules):
        rules = RuleString(rules)
        rule_num = 0
        num_matches = 0
        while not rules.eof():
            if self.asmrp_rule(rules):
                self.matches.append(rule_num)
                num_matches += 1
            rule_num += 1
        return self.matches

    @staticmethod
    def asmrp_match(rules, symbols):
        asmrp = Asmrp(rules, symbols)
        return asmrp.asmrp_eval(rules), asmrp.symbols


class RDTDatagram(object):
    'An RTP protocol datagram parser'

    prev_timestamp = None
    out_file = None
    prev_timestamp = None
    prev_stream_num = None
    streamids = []
    setup_streamids = []
    ended_streamids = []

    EOF = 0xff06
    LATENCY_REPORT = 0xff08

    def __init__(self):

        self.end_stream = False
        self.num_packets = 0
        self.data_size = 0
        self.out_file = StringIO.StringIO()        

    def select_mlti_data(self, mlti_chunk, selection):
        """ Takes a MLTI-chunk from an SDP OpaqueData and a rule selection
        Returns the codec data based on the given rule selection """
        if selection <= 0:
            return 0
        selection -= selection
        if not mlti_chunk.startswith('MLTI'):
            #print('MLTI tag missing')
            return mlti_chunk
        idx = 4 # past 'MLTI'
        numrules = struct.unpack('!H', mlti_chunk[idx:idx + 2])[0]
        idx += 2
        rules = []
        for i in range(0, numrules):
            rules.append(struct.unpack('!H', mlti_chunk[idx:idx + 2])[0])
            idx += 2
        if selection > numrules:
            return 0
        numcodecs = struct.unpack('!H', mlti_chunk[idx:idx + 2])[0]
        idx += 2
        codecs = []
        for i in range(numcodecs):
            codec_length = struct.unpack('!I', mlti_chunk[idx:idx + 4])[0]
            idx += 4 # skip over codec length integer
            codecs.append(mlti_chunk[idx:idx + codec_length])
            idx += codec_length # skip over codec length worth of data
        return codecs[rules[selection]]

    def handleSdp(self, data):
        """ Called with SDP Response data
        Uses the SDP response to construct the file header """
        sdp = Sdpplin(data)
        header = rmff_header_t()
        try: abstract = sdp['Abstract']
        except KeyError: abstract = ''
        header.fileheader = rmff_fileheader_t(4 + sdp['StreamCount'])
        try: title = sdp['Title']
        except KeyError: title = ''
        try: author = sdp['Author']
        except KeyError: author = ''
        try: copyright = sdp['Copyright']
        except KeyError: copyright = ''
        header.cont = rmff_cont_t(title, author,
                                  copyright, abstract)
        header.data = rmff_data_t(0, 0)

        duration = 0
        max_bit_rate = 0
        avg_bit_rate = 0
        max_packet_size = 0
        avg_packet_size = None

        self.streammatches = {}

        # the rulebook is sometimes truncated and spread across the streams
        # not sure if this is common, or even the correct way to handle it
        rulebook = ''.join([s['ASMRuleBook'] for s in sdp.streams])
        #symbols = {'Bandwidth':self.factory.bandwidth,'OldPNMPlayer':'0'}
        symbols = {'Bandwidth':0,'OldPNMPlayer':'0'}
        rulematches, symbols = Asmrp.asmrp_match(rulebook, symbols)
        # Avg packet size seems off
        for s in sdp.streams:
            self.streammatches[s['streamid']] = rulematches
            mlti = self.select_mlti_data(s['OpaqueData'], rulematches[0])

            # some streams don't have the starttime, but do have endtime
            # and other meta data
            try: start_time = s['StartTime']
            except: start_time = 0

            mdpr = rmff_mdpr_t(s['streamid'], s['MaxBitRate'],
                               s['AvgBitRate'], s['MaxPacketSize'],
                               s['AvgPacketSize'], start_time,
                               s['Preroll'], s.duration,
                               s['StreamName'], s['mimetype'], mlti)
            header.streams.append(mdpr)
            if s.duration > duration:
                duration = s.duration
            if mdpr.max_packet_size > max_packet_size:
                max_packet_size = mdpr.max_packet_size
            max_bit_rate += mdpr.max_bit_rate
            avg_bit_rate += mdpr.avg_bit_rate
            if avg_packet_size is None:
                avg_packet_size = mdpr.avg_packet_size
            else:
                avg_packet_size = (avg_packet_size + mdpr.avg_packet_size)/2
        header.prop = rmff_prop_t(max_bit_rate, avg_bit_rate,
                                  max_packet_size, avg_packet_size,
                                  0, duration, 0, 0, 0, sdp['StreamCount'],
                                  sdp['Flags'])
        return header

    def parse(self, sdp, data):

        if len(data) <= 10:
            return
        self.header = self.handleSdp(sdp)
        self.streamids = [i for i in range(self.header.prop.num_streams)]
        header, data = data[:10], data[10:]
        packet_flags = struct.unpack("B", header[0])[0]
        packet_type = struct.unpack("!H", header[1:3])[0]
        if packet_type == self.EOF:
            # EOF Flags:
            #   1... .... = Need reliable: 1
            #   .000 01.. = Stream ID: 1
            #   .... ..1. = Packet sent: 1
            #   .... ...0 = Ext Flag: 0
            streamid = (packet_flags >> 2) & 0x1F
            if streamid not in self.ended_streamids:
                self.ended_streamids.append(streamid)
            # Waits for all streamids to send their EOF
            if len(self.streamids) != len(self.ended_streamids):
                return
            self.handleStreamEnd()
        if packet_type == self.LATENCY_REPORT:
            return
        
        timestamp = struct.unpack('!I', header[4:8])[0]
        stream_num = (packet_flags >> 1) & 0x1f
        flags2 = struct.unpack('B', header[3])[0]

        # Creates the rmff_header_t which is
        # inserted between packets for output
        rmff_ph = rmff_pheader_t()
        rmff_ph.length = len(data) + 12 # + 12 for the size of rmff_ph
        rmff_ph.stream_number = stream_num
        rmff_ph.timestamp = timestamp
        if (flags2 & 0x01) == 0 and (self.prev_timestamp != timestamp or self.prev_stream_num != stream_num):
            # I believe this flag signifies a stream change
            self.prev_timestamp = timestamp
            self.prev_stream_num = stream_num
            rmff_ph.flags = 2
        else:
            rmff_ph.flags = 0

        self.handleRDTData(data, rmff_ph)

    def handleStreamEnd(self):
        self.header.prop.num_packets = self.num_packets
        self.header.data.num_packets = self.num_packets
        self.header.data.size += self.data_size
        self.end_stream = True

    def handleRDTData(self, data, rmff_ph):
        self.num_packets += 1
        self.data_size += len(data)
        rmff_str = str(rmff_ph)
        self.data_size += len(rmff_str)
        self.out_file.write(rmff_str)
        self.out_file.write(data)

    def close(self):

        self.out_file.close()
