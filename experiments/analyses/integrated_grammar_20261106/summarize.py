"""Public aggregate only; private sentences/quotes remain in private artifacts."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,dumps
HERE=Path(__file__).resolve().parent

def main():
    runs=[]
    for p in sorted((ROOT/'experiments/runs').glob('*_integrated_grammar_*')):
        if not (p/'metrics.json').exists():continue
        runs.append({'run_id':p.name,'config':read(p/'config.json'),'metrics':read(p/'metrics.json'),
                     'postflight':read(p/'postflight.json')})
    paired=read(HERE/'private/analysis_repair_comparison.json')
    review=[]
    for who in ('claude','codex'):
        for phase in ('development','regression','repair'):
            p=HERE/'private'/who/(phase+'_review.json')
            review.append({'reviewer':who,'phase':phase,'received':p.exists(),
                           'reviewed_records':len(read(p)['reviewed_ids']) if p.exists() else 0})
    result={'task':'integrated_grammar_20261106','graph':read(HERE/'statistics_r2.json'),
            'runs':runs,'actual_model_calls':sum(r['metrics']['api_attempts'] for r in runs),
            'reported_tokens_sum':sum(r['metrics']['reported_usage']['total_tokens'] for r in runs),
            'usage_missing_calls':sum(r['metrics']['calls_without_usage'] for r in runs),
            'input_execution_count':sum(r['metrics']['records'] for r in runs),
            'unique_inputs':80,'independent_evaluation_inputs':0,
            'paired_analysis_checks':{'before':sum(c['before']['matches'] for c in paired['checks']),
                                      'after':sum(c['after']['matches'] for c in paired['checks']),
                                      'checks':len(paired['checks']),'controls':paired['controls']},
            'reviews':review,'tests':{'integrated':22,'runner':4,'reference_delivery':8,'existing_management':38},
            'claim_limits':['No naturalness score or KG superiority estimate.',
                            '26-package semantic refinement is incomplete.',
                            'Reference delivery alternative was replayed offline, not used in these model runs.',
                            'Observation fix was made after model runs; no post-fix Qwen run.',
                            'Neo4j database not replaced; graph file candidate used.',
                            'Local recovery commits only; no remote push.']}
    save(HERE/'summary.json',result)
    print(dumps({k:result[k] for k in ('actual_model_calls','reported_tokens_sum','usage_missing_calls','input_execution_count','reviews')}))

if __name__=='__main__':main()
