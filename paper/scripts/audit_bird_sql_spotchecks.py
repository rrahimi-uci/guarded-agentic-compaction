"""Reexecute ten retained BIRD predictions against archive-verified databases.

Requires the pinned local BIRD dev cache; performs no acquisition or provider
calls. Run from any directory with PYTHONPATH=src python path/to/this/script.py.
"""
import hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'paper/scripts'))
import bird_sql_agent_study as b
def main():
    cache=ROOT/'benchmarks/.cache/bird';base=b.BIRD_DIR
    archive_hash=hashlib.file_digest((cache/'dev.zip').open('rb'),'sha256').hexdigest()
    assert archive_hash==b.BIRD_ARCHIVE_SHA256
    with zipfile.ZipFile(cache/'dev.zip') as outer:
     assert hashlib.sha256(outer.read('dev_20240627/dev.json')).hexdigest()==hashlib.file_digest((base/'dev.json').open('rb'),'sha256').hexdigest()
     with outer.open('dev_20240627/dev_databases.zip') as f: nested_hash=hashlib.file_digest(f,'sha256').hexdigest()
    assert nested_hash==hashlib.file_digest((base/'dev_databases.zip').open('rb'),'sha256').hexdigest()
    qs={q['question_id']:q for q in b.load_questions()}; records=[]; dbhashes={}
    with zipfile.ZipFile(base/'dev_databases.zip') as databases:
     for db in b.families(list(qs.values())):
      entry=next(n for n in databases.namelist() if n.endswith('/'+db+'.sqlite'))
      with databases.open(entry) as f: expected=hashlib.file_digest(f,'sha256').hexdigest()
      local=base/'dev_databases'/db/(db+'.sqlite')
      assert expected==hashlib.file_digest(local.open('rb'),'sha256').hexdigest()
      dbhashes[db]=expected
      rows=json.loads(((ROOT/'paper/results/bird/schema_first')/db/'evaluation.json').read_text())['results']
      for quality in (True,False):
       row=next(r for r in rows if r['condition']=='compiled' and r['quality']['overall']==quality)
       q=qs[row['issue_number']]
       gold,error=b.execute_full(db,q['SQL']);assert gold is not None,(db,error)
       actual=b.grade(db,(gold,error),row['answer'],row['tool_sequence'])
       assert actual['overall']==quality,(db,row['issue_number'])
       records.append({'database':db,'question_id':row['issue_number'],'condition':'compiled','retained_correct':quality,'reexecuted_correct':actual['overall'],'prediction_error':actual['prediction_error'],'gold_result_rows':len(gold)})
    out={'review_date':'2026-10-08','provider_calls_executed':0,'scope':'Ten selected compiled outputs: one correct and one incorrect per primary database. Reexecution against archive-verified SQLite files; not an exhaustive independent grader implementation.','archive_sha256':archive_hash,'database_sha256':dbhashes,'records':records}
    (ROOT/'paper/results/bird/sql_spotcheck_audit.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('10/10 retained labels reproduced; five database hashes verified against the pinned archive; provider calls 0')


if __name__ == "__main__":
    main()
