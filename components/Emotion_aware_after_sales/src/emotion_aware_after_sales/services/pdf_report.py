"""Shared, in-memory dashboard PDF reports."""
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape

def build_pdf(title, filters, kpis, rows, notes=''):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4, landscape
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 8
    styles['BodyText'].leading = 11
    def p(value):
        return Paragraph(escape(str(value if value is not None else 'Unavailable')), styles['BodyText'])
    story = [Paragraph(escape(title), styles['Title']),
             p('Generated: '+datetime.now(ZoneInfo('Asia/Colombo')).strftime('%Y-%m-%d %H:%M %Z')),
             p('SYNTHETIC RESEARCH DATA - Human verification required.'),
             p('Filters: '+ '; '.join(f'{k}: {v}' for k,v in filters.items())), Spacer(1,12),
             Paragraph('KPI summary',styles['Heading2'])]
    story += [p(f'{k}: {v}') for k,v in kpis.items()]
    if notes: story += [Spacer(1,8),p(notes)]
    story += [Spacer(1,14),Paragraph('Filtered records',styles['Heading2'])]
    rows = list(rows)
    if rows:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        # Split wide registers into readable panels; repeat identifiers in each panel.
        identity = fields[:2]
        panels = [fields] if len(fields)<=7 else [identity+fields[i:i+5] for i in range(2,len(fields),5)]
        for fields in panels:
            table = LongTable([[p(k.replace('_',' ').title()) for k in fields]]+
                              [[p(row.get(k)) for k in fields] for row in rows],
                              colWidths=[770/len(fields)]*len(fields),repeatRows=1)
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf3')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#cbd5e1')),
                ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            story += [table,Spacer(1,14)]
    else: story += [p('No records match these filters.')]
    def footer(canvas, doc):
        canvas.setFont('Helvetica',8)
        canvas.drawRightString(805,18,f'Page {doc.page}')
    SimpleDocTemplate(output,pagesize=landscape(A4),rightMargin=35,leftMargin=35,
                      topMargin=30,bottomMargin=35).build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
