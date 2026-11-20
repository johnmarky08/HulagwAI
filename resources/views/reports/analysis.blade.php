<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HulagwAI analysis report</title>
<style>
  @page { margin: 22mm 16mm 18mm 16mm; }
  body { font-family: DejaVu Sans, sans-serif; font-size: 9.5pt; color: #1b1f2a; }
  h1 { font-size: 20pt; margin: 0; color: #3f35c7; }
  h2 { font-size: 12pt; margin: 18px 0 6px; color: #3f35c7; border-bottom: 1px solid #d6d8f0; padding-bottom: 3px; }
  .muted { color: #6b7080; font-size: 8.5pt; }
  table { width: 100%; border-collapse: collapse; margin: 4px 0; }
  th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid #e6e7f2; vertical-align: top; }
  th { background: #f1f1fb; font-size: 8.5pt; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-weight: bold; font-size: 10pt; }
  .real { background: #d7f5e8; color: #0b7a4b; }
  .ai_generated { background: #fde0e6; color: #b3203f; }
  .inconclusive { background: #fff0cc; color: #8a6100; }
  .bar { height: 10px; background: #e8e9f5; border-radius: 5px; width: 100%; }
  .bar > div { height: 10px; border-radius: 5px; background: #e04462; }
  .box { border: 1px solid #d6d8f0; background: #f7f7fd; padding: 8px 10px; border-radius: 4px; margin: 6px 0; }
  .mono { font-family: DejaVu Sans Mono, monospace; font-size: 7.5pt; word-break: break-all; }
  .cm td { text-align: center; font-weight: bold; }
  .sev-strong_ai { color: #b3203f; font-weight: bold; } .sev-info { color: #3f35c7; } .sev-weak_real { color: #0b7a4b; }
</style>
</head>
<body>
@php
  $r = $full['result'];
  $f = $full['file'];
  $pct = fn ($v, $d = 1) => is_numeric($v) ? number_format($v * 100, $d).'%' : '—';
  $n4  = fn ($v) => is_numeric($v) ? number_format($v, 4) : '—';
  $t   = $metrics['test'] ?? null;
@endphp

<h1>HulagwAI — Image analysis report</h1>
<div class="muted">Report for analysis {{ $rec['id'] }} · generated {{ $generatedAt }}</div>

<h2>1. Verdict</h2>
<table><tr>
  <td style="width:34%; border:none">
    @if($image)<img src="{{ $image }}" style="max-width: 100%; max-height: 190px; border-radius: 4px">@endif
  </td>
  <td style="border:none">
    <span class="badge {{ $r['verdict'] }}">{{ $r['label'] }}</span>
    <p style="font-size: 22pt; margin: 8px 0 0"><b>{{ $r['ai_percent'] }}%</b> <span class="muted">estimated AI likelihood</span></p>
    <div class="bar"><div style="width: {{ $r['ai_percent'] }}%"></div></div>
    <table style="margin-top:6px"><tr><td style="border:none">AI-generated: <b>{{ $r['ai_percent'] }}%</b></td><td style="border:none">Real: <b>{{ $r['real_percent'] }}%</b></td><td style="border:none">Model confidence: <b>{{ $r['confidence_percent'] }}%</b></td></tr></table>
    <p>{{ $r['explanation'] }}</p>
    <p class="muted">Decision source: {{ $r['decision_source'] === 'provenance' ? 'embedded provenance metadata' : 'machine-learning ensemble' }}</p>
  </td>
</tr></table>
<div class="box muted"><b>How to read this score.</b> {{ $r['how_to_read'] }} Detection is probabilistic and can be wrong in either direction; compression, editing and newer image generators can affect reliability.</div>


@php
  $attr = (array) ($full['result']['attribution'] ?? []);
  $ev = (array) ($full['result']['evidence'] ?? []);
  $am = $metrics['attribution'] ?? null;
@endphp
<h2>2a. Likely generator</h2>
@if(!empty($attr['available']))
  <p><b>{{ $attr['headline'] }}</b>
  <span class="muted">({{ ($attr['source'] ?? 'model') === 'metadata' ? 'named in the file itself' : 'estimated by the attribution model' }})</span></p>
  <table><tr><th>Candidate family</th><th class="num">Probability</th></tr>
  @foreach($attr['top'] as $cand)
    <tr><td>{{ $cand['label'] }}</td><td class="num">{{ $cand['percent'] }}%</td></tr>
  @endforeach</table>
  @if(!empty($attr['note']))<p class="muted">{{ $attr['note'] }}</p>@endif
@else
  <p class="muted">Generator attribution is not available for this image ({{ str_replace('_', ' ', $attr['reason'] ?? 'not computed') }}).</p>
@endif
<p class="muted">{{ $attr['disclaimer'] ?? config('hulagwai.notice.attribution') }}</p>

<h2>2b. Why it may look AI-generated</h2>
@if(count($ev['flags'] ?? []))
  <table><tr><th style="width:14%">Strength</th><th style="width:20%">Category</th><th>Observation</th></tr>
  @foreach($ev['flags'] as $fl)
    <tr><td class="sev-{{ $fl['strength'] === 'strong' ? 'strong_ai' : ($fl['strength'] === 'moderate' ? 'info' : 'weak_real') }}">{{ $fl['strength'] }}</td><td>{{ $fl['category'] }}</td><td><b>{{ $fl['title'] }}</b><br>{{ $fl['detail'] }}</td></tr>
  @endforeach</table>
@else
  <p class="muted">No specific signals stood out for this image.</p>
@endif
@if($heatmap)
  <p class="muted" style="margin-bottom:2px">Detector heat map: warmer colours mark patches the pixel-level detector scores as more AI-like.</p>
  <img src="{{ $heatmap }}" style="max-width: 62%; border-radius: 4px">
@endif
<p class="muted">{{ $ev['note'] ?? config('hulagwai.notice.evidence') }}</p>

<h2>2. File</h2>
<table>
  <tr><th style="width:26%">File name</th><td>{{ $f['filename'] }}</td></tr>
  <tr><th>Format / size</th><td>{{ $f['format'] }} · {{ number_format($f['size_bytes'] / 1024, 1) }} KB ({{ $f['size_mb'] }} MB)</td></tr>
  <tr><th>Dimensions</th><td>{{ $f['width'] }} × {{ $f['height'] }} px</td></tr>
  <tr><th>SHA-256</th><td class="mono">{{ $rec['sha256'] }}</td></tr>
  <tr><th>Analyzed on</th><td>{{ $rec['analyzed_at'] }}</td></tr>
</table>

<h2>3. Model components for this image</h2>
@php $comp = (array) ($details['components'] ?? []); @endphp
@if(count($comp))
<table>
  <tr><th>Component</th><th class="num">P(AI)</th><th class="num">Weight in ensemble</th><th>Role</th></tr>
  @foreach($comp as $name => $c)
    <tr><td>{{ $name }}</td><td class="num">{{ $pct($c['p'] ?? null) }}</td><td class="num">{{ isset($c['weight']) ? $n4($c['weight']) : '—' }}</td><td>{{ $c['role'] ?? '' }}</td></tr>
  @endforeach
</table>
@if(isset($details['decision']['disagreement']))
  <p class="muted">Disagreement between components (std. dev. of probabilities): {{ $n4($details['decision']['disagreement']) }}.
  Thresholds used — Real ≤ {{ $details['thresholds']['real_max'] ?? '—' }}, AI ≥ {{ $details['thresholds']['ai_min'] ?? '—' }}; in between = Inconclusive.</p>
@endif
@else
  <p class="muted">No ML components ran for this image (the decision came from provenance metadata or the ML model was not installed).</p>
@endif

<h2>4. Metadata &amp; provenance findings</h2>
@php $fi = (array) ($details['metadata']['findings'] ?? []); @endphp
@if(count($fi))
<table>
  <tr><th style="width:18%">Severity</th><th>Finding</th><th>Evidence</th></tr>
  @foreach($fi as $x)
    <tr><td class="sev-{{ $x['severity'] ?? 'info' }}">{{ str_replace('_', ' ', $x['severity'] ?? 'info') }}</td><td>{{ $x['title'] ?? '' }}</td><td class="mono">{{ $x['evidence'] ?? '' }}</td></tr>
  @endforeach
</table>
@else
  <p>No AI-provenance markers, generator signatures or C2PA manifests were found. Absence of metadata is common (social networks strip it) and is not evidence either way.</p>
@endif
@if(!empty($details['metadata']['c2pa']['present']))
  <p class="muted">A C2PA/JUMBF container is present. Its signature was <b>not</b> cryptographically verified by this system.</p>
@endif

@if(!empty($details['warnings']))
<h2>5. Quality warnings</h2>
<ul>@foreach($details['warnings'] as $w)<li>{{ str_replace('_', ' ', $w) }}</li>@endforeach</ul>
@endif

<h2>6. Model &amp; evaluation metrics</h2>
@if($model)
<table>
  <tr><th style="width:26%">Model</th><td>{{ $model->name }} v{{ $model->version }}</td></tr>
  <tr><th>Weights SHA-256</th><td class="mono">{{ $model->weights_sha256 }}</td></tr>
  <tr><th>Evaluated</th><td>{{ $model->evaluated_at ? $model->evaluated_at->toDayDateTimeString() : 'not evaluated' }}</td></tr>
</table>
@endif

@if($t)
<p class="muted">Computed on a held-out test split of {{ number_format($t['n'] ?? 0) }} images that were never used for training or threshold fitting (decision threshold {{ $t['threshold'] ?? 0.5 }}).</p>
<table>
  <tr><th>Metric</th><th class="num">Value</th><th>Metric</th><th class="num">Value</th></tr>
  <tr><td>Accuracy</td><td class="num">{{ $pct($t['accuracy'] ?? null, 2) }}</td><td>ROC-AUC</td><td class="num">{{ $n4($t['roc_auc'] ?? null) }}</td></tr>
  <tr><td>Precision (AI class)</td><td class="num">{{ $pct($t['precision'] ?? null, 2) }}</td><td>Average precision (PR-AUC)</td><td class="num">{{ $n4($t['average_precision'] ?? null) }}</td></tr>
  <tr><td>Recall / sensitivity</td><td class="num">{{ $pct($t['recall'] ?? null, 2) }}</td><td>MAE (|p − label|)</td><td class="num">{{ $n4($t['mae'] ?? null) }}</td></tr>
  <tr><td>Specificity</td><td class="num">{{ $pct($t['specificity'] ?? null, 2) }}</td><td>MSE</td><td class="num">{{ $n4($t['mse'] ?? null) }}</td></tr>
  <tr><td>F1 score</td><td class="num">{{ $n4($t['f1'] ?? null) }}</td><td>RMSE</td><td class="num">{{ $n4($t['rmse'] ?? null) }}</td></tr>
  <tr><td>Balanced accuracy</td><td class="num">{{ $pct($t['balanced_accuracy'] ?? null, 2) }}</td><td>Brier score</td><td class="num">{{ $n4($t['brier'] ?? null) }}</td></tr>
  <tr><td>Matthews corr. coef. (MCC)</td><td class="num">{{ $n4($t['mcc'] ?? null) }}</td><td>Log loss</td><td class="num">{{ $n4($t['log_loss'] ?? null) }}</td></tr>
  <tr><td>False-positive rate</td><td class="num">{{ $pct($t['fpr'] ?? null, 2) }}</td><td>Expected calibration error (ECE)</td><td class="num">{{ $n4($t['ece'] ?? null) }}</td></tr>
  <tr><td>False-negative rate</td><td class="num">{{ $pct($t['fnr'] ?? null, 2) }}</td><td>Negative predictive value</td><td class="num">{{ $pct($t['npv'] ?? null, 2) }}</td></tr>
</table>

@if(isset($t['confusion']))
<h2>Confusion matrix (test split)</h2>
<table class="cm" style="width:60%">
  <tr><th></th><th>Predicted real</th><th>Predicted AI</th></tr>
  <tr><th>Actually real</th><td>{{ number_format($t['confusion']['tn']) }} <div class="muted">TN</div></td><td>{{ number_format($t['confusion']['fp']) }} <div class="muted">FP</div></td></tr>
  <tr><th>Actually AI</th><td>{{ number_format($t['confusion']['fn']) }} <div class="muted">FN</div></td><td>{{ number_format($t['confusion']['tp']) }} <div class="muted">TP</div></td></tr>
</table>
@endif

@if(!empty($metrics['selective']))
<h2>Three-way verdict behaviour</h2>
<table>
  <tr><th>Coverage (decided)</th><th>Accuracy when decided</th><th>Inconclusive rate</th></tr>
  <tr><td>{{ $pct($metrics['selective']['coverage'] ?? null, 1) }}</td><td>{{ $pct($metrics['selective']['accuracy_decided'] ?? null, 2) }}</td><td>{{ $pct($metrics['selective']['inconclusive_rate'] ?? null, 1) }}</td></tr>
</table>
@endif

@if(!empty($metrics['comparison']['rows']))
<h2>Model comparison (baselines vs final model)</h2>
<table><tr><th>Model</th><th>Type</th><th class="num">Accuracy</th><th class="num">Recall</th><th class="num">F1</th><th class="num">ROC-AUC (test)</th><th class="num">ROC-AUC (val)</th></tr>
@foreach($metrics['comparison']['rows'] as $c)
  <tr><td>{{ $c['name'] }}@if(($c['family'] ?? '') === 'final') <b>(selected)</b>@endif</td><td>{{ $c['family'] ?? '' }}</td><td class="num">{{ $pct($c['accuracy'] ?? null) }}</td><td class="num">{{ $pct($c['recall'] ?? null) }}</td><td class="num">{{ $n4($c['f1'] ?? null) }}</td><td class="num">{{ $n4($c['roc_auc'] ?? null) }}</td><td class="num">{{ $n4($c['val_roc_auc'] ?? null) }}</td></tr>
@endforeach</table>
<p class="muted">{{ $metrics['comparison']['basis'] ?? '' }}</p>
@endif

@if(!empty($metrics['cross_validation']))
<p class="muted"><b>5-fold cross-validation</b> (training split): accuracy {{ $pct($metrics['cross_validation']['accuracy']['mean'] ?? null, 2) }} ± {{ $pct($metrics['cross_validation']['accuracy']['std'] ?? null, 2) }}, ROC-AUC {{ $n4($metrics['cross_validation']['roc_auc']['mean'] ?? null) }} ± {{ $n4($metrics['cross_validation']['roc_auc']['std'] ?? null) }}.</p>
@endif

@if(!empty($metrics['errors']['by_resolution']))
<h2>Error analysis by image size</h2>
<table><tr><th>Image size</th><th class="num">Images</th><th class="num">Accuracy</th></tr>
@foreach($metrics['errors']['by_resolution'] as $k => $v)
  <tr><td>{{ $k }}</td><td class="num">{{ number_format($v['n'] ?? 0) }}</td><td class="num">{{ $pct($v['accuracy'] ?? null) }}</td></tr>
@endforeach</table>
<p class="muted">{{ $metrics['errors']['note'] ?? '' }}</p>
@endif

@if(!empty($am['test']))
<h2>Generator-attribution model (held-out test)</h2>
<p class="muted">Closed set of {{ count($am['families'] ?? []) }} generator families; chance level {{ $pct($am['test']['chance_level'] ?? null) }}. Answers "unknown" below confidence τ = {{ $am['tau'] ?? '—' }}.</p>
<table>
  <tr><th>Accuracy</th><th>Top-3 accuracy</th><th>Macro-F1</th><th>Coverage (answered)</th><th>Accuracy when answered</th><th>ECE</th></tr>
  <tr><td>{{ $pct($am['test']['accuracy'] ?? null, 2) }}</td><td>{{ $pct($am['test']['top3_accuracy'] ?? null, 2) }}</td><td>{{ $n4($am['test']['macro_f1'] ?? null) }}</td><td>{{ $pct($am['test']['coverage'] ?? null) }}</td><td>{{ $pct($am['test']['accuracy_when_accepted'] ?? null, 2) }}</td><td>{{ $n4($am['test']['ece'] ?? null) }}</td></tr>
</table>
<table><tr><th>Family</th><th class="num">Images</th><th class="num">Precision</th><th class="num">Recall</th><th class="num">F1</th></tr>
@foreach(($am['test']['per_family'] ?? []) as $fam => $fm)
  <tr><td>{{ $am['labels'][$fam] ?? $fam }}</td><td class="num">{{ number_format($fm['n'] ?? 0) }}</td><td class="num">{{ $pct($fm['precision'] ?? null) }}</td><td class="num">{{ $pct($fm['recall'] ?? null) }}</td><td class="num">{{ $n4($fm['f1'] ?? null) }}</td></tr>
@endforeach</table>
<p class="muted">{{ $am['note'] ?? '' }}</p>
@endif

@if(!empty($metrics['per_source']))
<h2>Per dataset</h2>
<table><tr><th>Dataset</th><th class="num">Images</th><th class="num">Accuracy</th><th class="num">Recall</th><th class="num">Specificity</th><th class="num">ROC-AUC</th></tr>
@foreach($metrics['per_source'] as $name => $m)
  <tr><td>{{ $name }}</td><td class="num">{{ number_format($m['n'] ?? 0) }}</td><td class="num">{{ $pct($m['accuracy'] ?? null) }}</td><td class="num">{{ $pct($m['recall'] ?? null) }}</td><td class="num">{{ $pct($m['specificity'] ?? null) }}</td><td class="num">{{ $n4($m['roc_auc'] ?? null) }}</td></tr>
@endforeach</table>
@endif

@if(!empty($metrics['per_generator']))
<h2>Detection rate per generator (recall)</h2>
<table><tr><th>Generator</th><th class="num">Images</th><th class="num">Recall</th></tr>
@foreach($metrics['per_generator'] as $name => $m)
  <tr><td>{{ $name }}</td><td class="num">{{ number_format($m['n'] ?? 0) }}</td><td class="num">{{ $pct($m['recall'] ?? null) }}</td></tr>
@endforeach</table>
@endif

@if(!empty($metrics['ood']))
<h2>Unseen-generator test (out-of-distribution)</h2>
<p class="muted">{{ $metrics['ood']['name'] ?? 'OOD set' }} — images from generators the model never saw in training.</p>
<table><tr><th>Fake images</th><th class="num">Recall</th><th>Real images</th><th class="num">Specificity</th></tr>
<tr><td>{{ number_format($metrics['ood']['n_fake'] ?? 0) }}</td><td class="num">{{ $pct($metrics['ood']['recall'] ?? null) }}</td><td>{{ isset($metrics['ood']['n_real']) ? number_format($metrics['ood']['n_real']) : 'not supplied' }}</td><td class="num">{{ $pct($metrics['ood']['specificity'] ?? null) }}</td></tr></table>
@endif

@if(!empty($metrics['robustness']))
<h2>Robustness (accuracy after common transformations)</h2>
<table><tr><th>Transformation</th><th class="num">Accuracy</th></tr>
@foreach($metrics['robustness'] as $name => $m)
  <tr><td>{{ str_replace('_', ' ', $name) }}</td><td class="num">{{ $pct($m['accuracy'] ?? null) }}</td></tr>
@endforeach</table>
@endif

@if(!empty($metrics['datasets']))
<h2>Training &amp; evaluation datasets</h2>
<table><tr><th>Dataset</th><th>Role</th><th>Source</th></tr>
@foreach($metrics['datasets'] as $d)
  <tr><td>{{ $d['name'] ?? '' }}</td><td>{{ $d['role'] ?? '' }}</td><td class="mono">{{ $d['url'] ?? '' }}</td></tr>
@endforeach</table>
@endif
@else
<div class="box"><b>Model has not been evaluated yet.</b> Metrics such as accuracy, precision, recall, F1, ROC-AUC and MAE belong to the <i>model</i>, not to a single image, and are produced by <span class="mono">ml-service/training/07_evaluate.py</span> after training. Until the bundle containing <span class="mono">metrics.json</span> is installed this section stays empty rather than showing placeholder numbers.</div>
@endif

<h2>Intended use, limitations &amp; responsible use</h2>
<p><b>Intended use.</b> {{ config('hulagwai.notice.intended_use') }}</p>
<ul>@foreach(config('hulagwai.notice.limitations') as $l)<li>{{ $l }}</li>@endforeach</ul>
<p><b>Responsible use.</b></p>
<ul>@foreach(config('hulagwai.notice.responsible_use') as $l)<li>{{ $l }}</li>@endforeach</ul>
<h2>Limitations</h2>
<p class="muted">HulagwAI is a statistical system. It can misclassify real photographs as AI-generated and vice-versa, especially for heavily compressed, screenshotted, resized or edited images, and for generators released after training. Embedded metadata can be removed or forged. Treat this report as one signal and verify the image's source before drawing conclusions.</p>
</body>
</html>
