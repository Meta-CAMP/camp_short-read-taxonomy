'''Utilities.'''


# --- Workflow setup --- #


import gzip
import os
from os import makedirs, symlink
from os.path import abspath, basename, exists, join
import pandas as pd
import shutil
import yaml


def get_conda_prefix(yaml_file):
    """Load conda_prefix from parameters.yaml."""
    with open(yaml_file, "r") as file:
        config = yaml.safe_load(file)
    return config.get("conda_prefix", "Not Found")  # Default value if key is missing


def extract_from_gzip(ap, out):
    if open(ap, 'rb').read(2) != b'\x1f\x8b': # If the input is not gzipped
        with open(ap, 'rb') as f_in, gzip.open(out, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    else: # Otherwise, symlink
        symlink(ap, out)


def ingest_samples(samples, tmp):
    df = pd.read_csv(samples, header = 0, index_col = 0) # name, fwd, rev
    s = list(df.index)
    lst = df.values.tolist()
    for i,l in enumerate(lst):
        if not exists(join(tmp, s[i] + '_1.fastq.gz')):
            extract_from_gzip(abspath(l[0]), join(tmp, s[i] + '_1.fastq.gz'))
            extract_from_gzip(abspath(l[1]), join(tmp, s[i] + '_2.fastq.gz'))
    return s


def check_make(d):
    if not exists(d):
        makedirs(d)


class Workflow_Dirs:
    '''Management of the working directory tree.'''
    OUT = ''
    TMP = ''
    LOG = ''

    def __init__(self, work_dir, module):
        self.OUT = join(work_dir, module)
        self.TMP = join(work_dir, 'tmp') 
        self.LOG = join(work_dir, 'logs') 
        check_make(self.OUT)
        out_dirs = ['0_masked_fastqs', '1_metaphlan', '2_kraken2', '3_xtree', 'final_reports']
        for d in out_dirs: 
            check_make(join(self.OUT, d))
        check_make(join(self.OUT,'1_metaphlan','raw_output'))
        check_make(join(self.OUT, '3_xtree', 'merged'))
        check_make(join(self.OUT, 'final_reports', 'unclassified'))
        check_make(self.TMP)
        check_make(self.LOG)
        log_dirs = ['masking', 'metaphlan', 'kraken2', 'bracken', 'xtree']       
        for d in log_dirs: 
            check_make(join(self.LOG, d))


def cleanup_files(work_dir, df):
    smps = list(df.index)
    for d in ['1', '2']:
         for s in smps:
            masked_fq = join(work_dir, 'short-read-taxonomy', '0_masked_fastqs', s + '_' + d + '.masked.fastq.gz')
            if exists(masked_fq):
                os.remove(masked_fq)
            os.remove(join(work_dir, 'short-read-taxonomy', '1_metaphlan', s + '_' + d + '.fastq'))
            os.remove(join(work_dir, 'short-read-taxonomy', '1_metaphlan', 'raw_output', s + '.sam'))
            os.remove(join(work_dir, 'short-read-taxonomy', '1_metaphlan', 'raw_output', s + '.dedup.sam'))
            os.remove(join(work_dir, 'short-read-taxonomy', '1_metaphlan', 'raw_output', s + '.dedup.txt'))
            os.remove(join(work_dir, 'short-read-taxonomy', '3_xtree', s + '.fastq'))


def print_cmds(f):
    # fo = basename(log).split('.')[0] + '.cmds'
    # lines = open(log, 'r').read().split('\n')
    fi = [l for l in f.split('\n') if l != '']
    write = False
    with open('commands.sh', 'w') as f_out:
        for l in fi:
            if 'rule' in l:
                f_out.write('# ' + l.strip().replace('rule ', '').replace(':', '') + '\n')
                write = False
            if 'wildcards' in l:
                f_out.write('# ' + l.strip().replace('wildcards: ', '') + '\n')
            if 'resources' in l:
                write = True
                l = ''
            if write:
                f_out.write(l.strip() + '\n')
            if 'rule make_config' in l:
                break


# --- Workflow functions --- #


import io


def scrub_fastq_captions(fi, fo):
    with io.TextIOWrapper(io.BufferedReader(gzip.open(fi, 'rb'))) as f_in, open(fo, 'w') as f_out:
        for l in f_in:
            if l.startswith('+'):
                f_out.write('+\n')
            else:
                f_out.write(l)


def reformat_row_meta(row, min_abund): 
    # Reshape into [rank, metaphlan, clade, second_elem, third_elem]
    clade_lst = row[0].split('|')
    if 't__' in clade_lst[-1]:
        return []
    else:
        raw_clade = clade_lst[-1] # Pick the lowest clade unless strain present, in which case skip
    if 'unclassified' in raw_clade:
        rank = 'u'
        clade = 'unclassified'
        tax_id = 'NaN'
    else:
        raw_clade_lst = raw_clade.split('__')
        rank = raw_clade_lst[0]
        clade = raw_clade_lst[1].replace('_', ' ')
        tax_id_lst = row[1].split('|')
        tax_id = tax_id_lst[-2] if rank == 't' else tax_id_lst[-1] # Like the above, pick the lowest clade's taxID
    rel_abund = row[2] / 100.0 if row[2] >= min_abund * 100.0 else 0
    return [rank, 'metaphlan', clade, tax_id, rel_abund]
        # MetaPhlan4 outputs the percentage numerator instead of decimals


# Process single-sample MetaPhlan reports into single-sample unified format report
# In:   #clade_name     NCBI_tax_id     relative_abundance      additional_species
# In:   k__Bacteria|p__Bacteroidetes    2|976   71.60402
# Out:  classifier,clade,taxid,sample_X_ra
def standardize_metaphlan(fi, out_dir, min_abund):
    raw_df = pd.read_csv(fi, sep = '\t', skiprows = 6, header = 0, index_col = None)
    sample = basename(fi).split('.')[0]
    out_lst = list(raw_df.apply(lambda row : reformat_row_meta(row, min_abund), axis = 1))
    basic_cols = ['classifier', 'clade', 'tax_id']
    out_df = pd.DataFrame(out_lst, columns = ['rank'] + basic_cols + [sample])
    for r, rank in { 's' : 'species', 'g' : 'genus', 'f' : 'family', 'o' : 'order', 'c' : 'class', 'p' : 'phylum'}.items():
        sub_df = out_df[out_df.iloc[:,0] == r]
        if not sub_df.empty:
            sub_df.drop(columns = sub_df.columns[0], axis = 1, inplace = True) # Get rid of rank column
        sub_df.to_csv(join(out_dir, sample + '_' + rank + '.csv'), header = True, index = False)


# Process single-sample Bracken reports into single-sample unified format report
# In: name    taxonomy_id     taxonomy_lvl    kraken_assigned_reads   added_reads new_est_reads   fraction_total_reads
# Out:  classifier,classification,taxid,sample_1_ra,sample_2_ra,sample_3_ra
def standardize_bracken(fi, out_dir, min_abund):
    raw_df = pd.read_csv(fi, sep = '\t', header = 0, index_col = None)
    abs_path = fi.split('/')
    sample = abs_path[-2]
    rank = abs_path[-1].split('.')[0]
    raw_df['classifier'] = 'kraken_bracken'
    raw_df[sample] = list(raw_df.apply(lambda row : row[6] if row[6] >= min_abund else 0, axis = 1))
    pruned_df = raw_df[['classifier', 'name', 'taxonomy_id', sample]]
    pruned_df.columns = ['classifier', 'clade', 'tax_id', sample]
    pruned_df.to_csv(join(out_dir, sample + '_' + rank + '.csv'), header = True, index = False)


def load_taxid(ncbi_taxid):
    n2i_df = pd.read_csv(ncbi_taxid, sep = "\t|\t", header = None, index_col = None)
    pruned_df = n2i_df.iloc[:,[0,2]]
    pruned_df.set_index(2, inplace = True)
    return {i : row for i, row in pruned_df.iterrows()} # This takes a long time


def reformat_row_xtree(row, n2i_dct, r):
    # Reshape into [rank, xtree, clade, sample_1_ra,...,sample_n_ra]
    raw_clade = 'NaN'
    for c in row[0].split(';'):
        if r + '__' in c:
            raw_clade = c
    if raw_clade == 'NaN':
        return
    raw_clade_lst = raw_clade.split('__')
    clade = raw_clade_lst[1].replace('_', ' ')
    clade_name_parts = clade.split()
    if len(clade_name_parts[-1]) == 1 and clade_name_parts[-1].isupper(): # Delete non-canonical information from taxon name
        clade = clade[:-2]
    tax_id = n2i_dct[clade][0] if clade in n2i_dct else 'NaN'
    new_row = ['xtree', clade, tax_id]
    new_row.extend(row[1:])
    return new_row


# Process merged XTree reports into merged unified format report
# In: NA    Xsample_1        Xsample_2        Xsample_3
# Out:  classifier,classification,taxid,sample_1_ra,sample_2_ra,sample_3_ra
def standardize_xtree(fi, out_dir, ncbi_taxid, uthresh):
    n2i_dct = load_taxid(ncbi_taxid)
    raw_df = pd.read_csv(fi, sep = '\t', header = 0, index_col = None)
    raw_df.reset_index(inplace = True)
    basic_cols = ['classifier', 'clade', 'tax_id']
    sample_names = list(raw_df.columns[1:])
    column_names = basic_cols + sample_names # 1 | all)
    for r, rank in { 's' : 'species', 'g' : 'genus', 'f' : 'family', 'o' : 'order', 'c' : 'class', 'p' : 'phylum'}.items():
        out_lst = list(raw_df.apply(lambda row : reformat_row_xtree(row, n2i_dct, r), axis = 1))
        filt_lst = [x for x in out_lst if x is not None]
        filt_df = pd.DataFrame(filt_lst, columns = column_names)
        filt_df.columns = column_names
        agg_dct = {}
        for c in basic_cols:
            agg_dct[c] = 'first'
        for c in sample_names:
            agg_dct[c] = 'sum'
        out_df = filt_df.groupby(filt_df['clade']).aggregate(agg_dct)
        out_df.reset_index(inplace = True, drop = True)
        out_df.mask(out_df[sample_names] < uthresh, inplace = True)
        out_df.dropna(axis = 0, how = 'all', subset = sample_names, inplace = True)
        for s in sample_names:
            out_df[s] = out_df[s].fillna(0)
        out_df.to_csv(join(out_dir, 'xtree_' + rank + '.csv'), header = True, index = False)


def concat_tbls(sample_lst, fo):
    s_lst = []
    tmp_colnames = []
    sample_names = []
    if len(sample_lst) == 1:
        shutil.copy(sample_lst[0], fo)
    else:
        for i,s in enumerate(sample_lst):
            df = pd.read_csv(s, header = 0)
            s_lst.append(df)
            sample = df.columns[-1]
            sample_names.append(sample)
            if i < len(sample_lst) - 1:
                tmp_colnames.extend(['tmp', 'tmp', 'tmp', sample])
            else:
                tmp_colnames.extend(df.columns)
        df = pd.concat(s_lst, axis = 1, join = 'outer')
        df.columns = tmp_colnames
        df.drop(columns = 'tmp', axis = 1, inplace = True) # Get rid of all but the last set of 'classifier, clade, tax_id'
        df = df[['classifier', 'clade', 'tax_id'] + sample_names]
        df.fillna(0)
        df.to_csv(fo, header = True, index = False)


def extract_unclassified_names(fi, fo):
    df = pd.read_csv(fi, sep = '\t', header = None, index_col = None)
    unc_reads = list(df[df[0] == 'U'][1])
    with open(fo, 'w') as f_out:
        for r in unc_reads:
            f_out.write(r + '\n')




