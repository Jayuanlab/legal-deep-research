from pathlib import Path
root=Path(__file__).parent
s=(root/'check-report-v2-render.cjs').read_text(encoding='utf-8')
s=s.replace("'legal-report-v2'","'legal-report-v3'").replace('runs/report-v2/render-validation.json','runs/report-v3/render-validation.json')
(root/'check-report-v3-render.cjs').write_text(s,encoding='utf-8')
