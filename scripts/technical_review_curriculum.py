"""Synthetic teaching briefs and evidence, never model-authored deliverables.

All measurements, organisations and prices below are fictional. The model must
reason from these supplied records, not present them as real experiments. Rubrics
are independent examiner notes and never enter generation messages.
"""
from scripts.technical_review_case import SOURCES


def card(identifier, notes):
    return {'id':identifier, 'title':'Synthetic exercise evidence: '+identifier,
            'url':'', 'checked_on':'2026-09-20',
            'scope':'Fictional teaching record only; not a real benchmark, vendor quote or client result.',
            'notes':notes}


CASES = [
    {'id':'evaluation', 'family':'review-training-ticket-experiment',
     'article':'''Choosing a Ticket Classifier
In our synthetic pilot, the base model correctly classified 82 of 100 test tickets and the tuned model classified 86 of the same 100 tickets.
This proves fine-tuning delivers a statistically significant four-percent accuracy improvement for every support team.
We selected the best checkpoint by evaluating all 24 checkpoints on those same 100 test tickets.
The tuned model is ready for production because its training loss decreased and its overall accuracy increased.
For a follow-up, we should compare a prompted base model and the tuned model using representative unseen tickets, a task-relevant metric and recorded serving measurements.
''',
     'sources':[card('ticket-log', 'Synthetic pilot: 100 tickets from one team; base correct=82, tuned correct=86. Paired per-ticket outcomes, confidence intervals and per-class counts were not supplied. All 24 checkpoints were compared on these tickets and the best score was selected. No latency, throughput, error-cost or regression measurements were collected.'), SOURCES[3]],
     'issues':{3:'Four percentage points, not four percent relative. No statistical significance, paired outcomes, uncertainty or cross-team guarantee established.',
               4:'Checkpoint selection is validation, not untouched final test. Re-evaluate a fixed procedure on a fresh test set; group related tickets appropriately.',
               5:'Training loss/aggregate accuracy do not establish deployment readiness: slice/error cost, regressions, latency, throughput and resource measurements.'},
     'controls':[2,6]},
    {'id':'memory', 'family':'review-training-memory-experiment',
     'article':'''Sizing a Fine-Tuning Job
LoRA freezes pretrained weights and trains low-rank update matrices for selected layers.
QLoRA trains every original base-model weight directly in four-bit precision, which is why its rank is always smaller than LoRA.
Our synthetic job used 22 GiB of peak allocated device memory with a 27B model, sequence length 2048, batch size one and rank eight.
Therefore any 27B QLoRA job will fit on a 24 GiB card, even at sequence length 32768 and batch size sixteen.
Freezing the base model removes the need to run the base model during training, so adapter training has no activation-memory cost.
''',
     'sources':[SOURCES[0],SOURCES[1],card('memory-log','Fictional run only: 27B base, four-bit loading, rank 8 adapters, sequence length 2048, microbatch 1, gradient checkpointing enabled. Peak allocated GPU memory reported as 22 GiB. Device-reserved memory, other processes, allocator overhead and higher sequence/batch configurations were not measured. No throughput result was recorded.')],
     'issues':{3:'Frozen quantized base; train adapters, not all base weights; rank independent of quantization.',
               5:'Specific allocated-memory measurement is not universal capacity proof; sequence/batch/implementation and reserved/other memory matter. Measure target workload.',
               6:'Freezing base parameters does not remove forward computation or gradient propagation/activations needed to train adapters.'},
     'controls':[2,4]},
    {'id':'cost', 'family':'review-training-fictional-costs',
     'article':'''The Cost of a Small Fine-Tuning Pilot
The following prices and workloads are fictional examples, not current provider quotes.
At two dollars per GPU-hour, one three-hour training run costs six dollars in GPU charges.
We ran four such training experiments, so total training GPU charges were still six dollars.
The complete first-month system cost was six dollars because endpoint hosting and storage are included in every fine-tuning service.
Our fictional endpoint runs continuously for 720 hours at fifty cents per hour; storage is twenty dollars for the month.
These inputs prove fine-tuning is cheaper than RAG for every application.
''',
     'sources':[card('cost-ledger','Fictional arithmetic exercise, USD: four training runs, each 3 GPU-hours at $2/GPU-hour; endpoint 720 hours at $0.50/hour; monthly storage $20. The scope excludes labour, data preparation, evaluation, networking and taxes. No provider offers or RAG baseline cost/quality results were supplied. All training runs occurred in that first month.')],
     'issues':{4:'Four runs cost $24.',5:'Hosting $360 plus storage $20 plus training $24 gives $404 for listed charges only, not all-in cost. No universal included-hosting assertion.',
               7:'No comparable RAG workload, quality or cost evidence; compare alternatives at task quality/latency requirements.'},
     'controls':[2,3,6]},
    {'id':'data', 'family':'review-training-synthetic-data-audit',
     'article':'''Preparing Synthetic Intent Labels
Our fictional audit reviewed 200 randomly sampled records from a generated dataset and found 18 incorrect intent labels.
Because a stronger teacher model generated the labels, all records can be treated as ground truth without further checks.
The observed error fraction in the audited sample was nine percent.
We can report an exact nine-percent error rate for every future generated dataset, regardless of teacher, prompt or domain.
There are 70 exact duplicate records and 35 pairs of paraphrases of the same source ticket spanning the training and test sets, but shuffling the rows fixes this leakage.
To improve reliability, label instructions and acceptance criteria should be defined before independently reviewing additional examples.
''',
     'sources':[card('label-audit','Fictional audit of 200 randomly sampled generated records from a 5000-record dataset found 18 incorrect intent labels. A separate deduplication scan found 70 exact duplicate records. A source-ticket grouping audit found 35 paraphrase pairs crossing training and test partitions. Future batches were not sampled or measured.'),SOURCES[3]],
     'issues':{3:'Teacher strength does not guarantee correct labels; independent review/quality criteria required.',
               5:'Observed sample fraction, with sampling uncertainty, not exact population or future-batch guarantee.',
               6:'Shuffling does not remove related-item leakage; deduplicate and partition by source family before fitting, rebuild untouched evaluation.'},
     'controls':[2,4,7]},
    {'id':'retrieval', 'family':'review-training-knowledge-freshness',
     'article':'''Keeping a Policy Assistant Current
Our fictional retrieval index contains policy documents as they stood on September 1; a policy changed on September 10 and the query arrived on September 12.
RAG guarantees an up-to-date answer on September 12 even though the changed document has not been ingested or indexed.
Fine-tuning on the September 1 documents also guarantees that the model will know the September 10 change without any further input.
Retrieval and a fine-tuned generator can be used together in one system.
Successful retrieval of a relevant paragraph guarantees the generated answer is factually supported, so end-to-end evaluation is unnecessary.
''',
     'sources':[SOURCES[2],card('policy-timeline','Fictional source/index timeline: indexed snapshot September 1; policy amended September 10; question September 12. No ingestion or reindexing after September 1, and the new policy was not otherwise supplied to the model. No retrieved passages, answer-grounding measurements or end-to-end evaluation results were supplied.')],
     'issues':{3:'Stale index cannot guarantee freshness; ingestion/index update/freshness monitoring and retrieval evaluation needed.',
               4:'Weights do not update from unseen external policy changes; factual learning is possible but not automatic external synchronization.',
               6:'Retrieval relevance does not guarantee generator grounding or correctness; assess retrieval and end-to-end answers, citations/abstention.'},
     'controls':[2,5]},
    {'id':'buyer', 'family':'review-training-enterprise-evidence',
     'article':'''Selecting an Enterprise Fine-Tuning Platform
In this fictional comparison, Vendor Cedar supplied a screenshot showing a private-endpoint checkbox; Vendor Elm supplied no security material.
The checkbox proves Cedar meets every enterprise security requirement and that customer data is never retained.
Elm is insecure because its security documentation was not included in our evidence pack.
Both vendors support every training method and deploy every model format at identical latency and cost in 2026.
We should request dated documentation and a reproducible workload-specific pilot before comparing suitability.
The final recommendation should identify the intended task, data restrictions, quality targets, serving constraints and the evidence missing from the comparison.
''',
     'sources':[card('vendor-pack','Fictional Cedar/Elm exercise only. Supplied artifacts: one Cedar screenshot of an unchecked option labelled private endpoint. No network test, contract, data retention policy, training-method support matrix, model compatibility list, pricing sheet or benchmark results. No Elm documentation. These are invented vendor names and not a ranking of actual providers.')],
     'issues':{3:'Checkbox is not tested isolation/retention/complete security proof; seek precise documentation/contracts and verification.',
               4:'Missing evidence means unknown, not demonstrated insecurity.',
               5:'Unsupported universal current capabilities and equal latency/cost; require dated supported configurations and matched workload tests.'},
     'controls':[2,6,7]},
]


def get_case(identifier):
    return next(case for case in CASES if case['id']==identifier)
