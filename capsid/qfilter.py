#!/usr/bin/env python

# Copyright 2011(c) The Ontario Institute for Cancer Reserach. All rights reserved.
#
# This program and the accompanying materials are made available under the
# terms of the GNU Public License v3.0.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import division
from itertools import count, ifilter, izip, imap, repeat
from collections import namedtuple
import os

from Bio import SeqIO

Records = namedtuple('Records', ['single', 'pair'])
FileName = namedtuple('FileName', ['name', 'dot', 'ext'])
Counter = namedtuple('Counter', ['records', 'saved'])

logger = None
threshold = None
limit = None
counter = Counter(count(), count())


def clean_ext(name):
    '''Pull off .fastq extension'''

    f = FileName._make(name.rpartition('.'))

    return f.name if f.ext == 'fastq' else name


def make_fastq_file(f):
    '''Turn 1-lined sorted temp file into fastq format'''
    fh = f + '.quality.fastq'
    logger.debug('Filtered Fastq: {0}'.format(fh))

    logger.info('Generating filtered Fastq file...')

    fq_sorted = open(f + '.collapsed')
    fastq = open(fh, 'w')

    [fastq.write('{0}\n{1}\n{2}\n{3}'.format(*line.split('\t')))
     for line in fq_sorted]


def collapse_file(f):
    ''' '''
    fc = f + '.collapsed'
    logger.debug('Collapsed File: {0}'.format(fc))
    logger.info('Collapsing {0}...'.format(fc))
    os.system('sort -u ' + f + '.temp -o ' + fc)


def sortable_output(record, fq_single, fq_pair):
    '''Output fastq records as 1-line into temp file so it can be sorted'''
    counter.saved.next()

    fq_single.write('@{description}\t{seq}\t+{description}\t{quality}\n'.format(
            description = record.single.description,
            seq = record.single.seq,
            quality = SeqIO.QualityIO._get_sanger_quality_str(record.single))
            )

    if fq_pair:
        fq_pair.write('@{description}\t{seq}\t+{description}\t{quality}\n'.format(
                description = record.pair.description,
                seq = record.pair.seq,
                quality = SeqIO.QualityIO._get_sanger_quality_str(record.pair))
                )


def make_sortable_file(records, f_single, f_pair):
    ''' '''
    ft_single = f_single + '.temp'
    ft_pair = f_pair + '.temp' if f_pair else None

    logger.debug('Temp File: {0}'.format(ft_single))
    if f_pair: logger.debug('Temp File: {0}'.format(ft_pair))

    logger.info('Creating temporary files for collapsing...')

    fh_single = open(ft_single, 'w')
    fh_pair = open(ft_pair, 'w') if f_pair else None
    [sortable_output(record, fh_single, fh_pair) for record in records]
    fh_single.close()
    if fh_pair: fh_pair.close()


def sort_unique(records, args):
    '''Sort fastq file and clean up'''

    f_single = clean_ext(args.single)
    f_pair = clean_ext(args.pair) if args.pair else None

    make_sortable_file(records, f_single, f_pair)

    collapse_file(f_single)
    make_fastq_file(f_single)

    if f_pair:
        collapse_file(f_pair)
        make_fastq_file(f_pair)


def quality_check(scores):
    '''Ensures that enough of the bases pass the quality threshold'''

    failed = len([q for q in scores if q < int(threshold)])

    return failed <= limit


def qual_eq_seq(scores):
    '''Checks that the length of the phred_quality is equal to the sequence '''

    return len(scores) == len(record.seq)


def valid_record(record):
    '''Return True if the records passes all tests'''
    counter.records.next()

    scores = record.letter_annotations['phred_quality']

    return len(scores) == len(record.seq) and quality_check(scores)


def filter_reads(records):
    '''Filters out records if both fail test'''

    return valid_record(records.single) or valid_record(records.pair)


def parse_fastq(args):
    ''' '''
    s = 'pair end' if args.pair else 'single end'
    logger.info('Reading Fastq files as {}...'.format(s))

    fq1 = SeqIO.parse(open(args.single, 'rU'), 'fastq')
    fq2 = SeqIO.parse(open(args.pair, 'rU'), 'fastq') if args.pair else repeat(None)

    return ifilter(filter_reads, imap(Records._make, izip(fq1, fq2)))


def summary(args):
    ''' '''

    # Counter starts at 0, so >it = count(); >print it.next(); >0
    # Using counter.*.next here sets it to the correct value for printing.
    records = counter.records.next()
    saved = counter.saved.next()

    if records:
        percent = (1 - saved/records) * 100
        logger.info('{0} filterd and saved to {1}.quality.fastq'.format(args.single, clean_ext(args.single)))
        if args.pair:
            logger.info('{0} collapsed and saved to {1}.quality.fastq'.format(args.pair, clean_ext(args.pair)))
        logger.info('{0} of {1} records saved'.format(saved, records))
        logger.info('{0:.2f}% of records removed'.format(percent))
    else:
        logger.warning('No records found.')


def main(args):
    ''' '''
    global db, logger, threshold, limit

    logger = args.logging.getLogger(__name__)
    threshold = int(args.threshold)
    limit = int(args.limit)

    records = parse_fastq(args)
    sort_unique(records, args)
    summary(args)

if __name__ == '__main__':
    print 'This program should be run as part of the capsid package:\n\t$ capsid qfilter -h\n\tor\n\t$ /path/to/capsid/bin/capsid qfilter -h'