import json
from pathlib import Path

from scripts import assess_technical_review_holdout as assessor


def test_assessor_requires_all_holdout_findings_and_rejects_fenced_json(tmp_path):
    # The fixture uses a real model-shaped response, but remains synthetic and
    # does not invoke a model or touch a private workspace.
    from scripts.technical_review_holdout import ARTICLE, SOURCES
    from scripts.check_technical_reviewer import messages_for
    run = tmp_path
    (run/'report.json').write_text(json.dumps({'status':'structurally_valid'}))
    content = json.dumps({'comments': [
        {'line':3,'quote':ARTICLE.splitlines()[2],'severity':'critical','issue':'future change RAG','recommendation':'future change RAG','source_ids':['pilot']},
        {'line':4,'quote':ARTICLE.splitlines()[3],'severity':'critical','issue':'QLoRA base adapter','recommendation':'QLoRA base adapter','source_ids':['qlora']},
        {'line':5,'quote':ARTICLE.splitlines()[4],'severity':'critical','issue':'checkpoint test leak','recommendation':'checkpoint test leak','source_ids':['pilot']},
        {'line':6,'quote':ARTICLE.splitlines()[5],'severity':'critical','issue':'cost retrieval comparison','recommendation':'cost retrieval comparison','source_ids':['pilot']},
    ],'top_fixes':['fix'],'citation_needs':[],'additions':['example'],'verdict':'needs_technical_revision','reader_intent':'intent','uncertainty':'limits'})
    (run/'correction-response-1.json').write_text(json.dumps({'content':'```json\n'+content+'\n```'}))
    result = assessor.assess(run)
    assert result['candidate_score'] == result['reference_score'] - 1
    assert result['parity_proven'] is False
