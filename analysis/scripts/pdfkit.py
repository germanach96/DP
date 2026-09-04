"""Layout primitives for the scope report. Palette matches the charts."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, Image, Table, TableStyle, KeepTogether, PageBreak, Flowable)

INK=colors.HexColor('#0b0b0b'); INK2=colors.HexColor('#52514e'); MUTED=colors.HexColor('#898781')
GRID=colors.HexColor('#e1e0d9'); AXIS=colors.HexColor('#c3c2b7'); SURF=colors.HexColor('#fcfcfb')
S1=colors.HexColor('#2a78d6'); S2=colors.HexColor('#eb6834'); S3=colors.HexColor('#1baf7a')
S4=colors.HexColor('#eda100'); S5=colors.HexColor('#e87ba4')
GOOD=colors.HexColor('#0ca30c'); WARN=colors.HexColor('#fab219')
SERIOUS=colors.HexColor('#ec835a'); CRIT=colors.HexColor('#d03b3b')
BAND=colors.HexColor('#f2f1ec'); BANDBLUE=colors.HexColor('#eef4fd')

F='Helvetica'; FB='Helvetica-Bold'; FI='Helvetica-Oblique'
PW,PH=A4
ML,MR,MT,MB=20*mm,18*mm,20*mm,18*mm
CW=PW-ML-MR

def P(n,**kw):
    d=dict(fontName=F,fontSize=9.6,leading=14.2,textColor=INK,spaceAfter=0,alignment=TA_LEFT)
    d.update(kw); return ParagraphStyle(n,**d)

ST={
 'h1':P('h1',fontName=FB,fontSize=21,leading=25,textColor=INK,spaceBefore=0,spaceAfter=3),
 'h2':P('h2',fontName=FB,fontSize=14.5,leading=18,textColor=INK,spaceBefore=11,spaceAfter=4,
        keepWithNext=True),
 'h3':P('h3',fontName=FB,fontSize=11,leading=14,textColor=INK,spaceBefore=11,spaceAfter=3,
        keepWithNext=True),
 'body':P('body',fontSize=9.5,leading=13.6,spaceAfter=6),
 'lead':P('lead',fontSize=10.6,leading=15,textColor=INK2,spaceAfter=8),
 'small':P('small',fontSize=8.4,leading=11.6,textColor=INK2),
 'cap':P('cap',fontSize=8.1,leading=10.6,textColor=MUTED,spaceBefore=3,spaceAfter=7),
 'kicker':P('kicker',fontName=FB,fontSize=8.2,leading=10,textColor=S1,spaceAfter=3),
 'bullet':P('bullet',fontSize=9.5,leading=13.6,leftIndent=11,bulletIndent=1,spaceAfter=4),
 'th':P('th',fontName=FB,fontSize=8.2,leading=10.4,textColor=INK),
 'td':P('td',fontSize=8.2,leading=10.4,textColor=INK),
 'tdm':P('tdm',fontSize=8.2,leading=10.4,textColor=INK2),
 'rule':P('rule',fontName=FB,fontSize=9.6,leading=13.6,textColor=INK,spaceAfter=3),
 'toc':P('toc',fontSize=9.8,leading=17,textColor=INK),
}

class HR(Flowable):
    def __init__(self,w=CW,c=GRID,t=0.7,pad=0):
        super().__init__(); self.w=w; self.c=c; self.t=t; self.pad=pad
    def wrap(self,*a): return (self.w,self.t+self.pad)
    def draw(self):
        self.canv.setStrokeColor(self.c); self.canv.setLineWidth(self.t)
        self.canv.line(0,self.pad/2,self.w,self.pad/2)

class Callout(Flowable):
    """A titled panel used for the rules and the 'what this means' boxes."""
    def __init__(self,title,body,accent=S1,bg=BANDBLUE,w=CW,icon=None):
        super().__init__(); self.w=w; self.accent=accent; self.bg=bg
        self.tp=Paragraph(f'<b>{title}</b>' if title else '',
                          P('ct',fontName=FB,fontSize=9.8,leading=13,textColor=INK))
        self.bp=Paragraph(body,P('cb',fontSize=9.3,leading=13.4,textColor=INK))
        self.icon=icon
    def wrap(self,aw,ah):
        iw=self.w-16-4
        self.th=self.tp.wrap(iw,ah)[1] if self.tp.text else 0
        self.bh=self.bp.wrap(iw,ah)[1]
        self.h=self.th+self.bh+(5 if self.th else 0)+16
        return (self.w,self.h)
    def draw(self):
        c=self.canv
        c.setFillColor(self.bg); c.rect(0,0,self.w,self.h,stroke=0,fill=1)
        c.setFillColor(self.accent); c.rect(0,0,3,self.h,stroke=0,fill=1)
        y=self.h-8
        if self.tp.text:
            y-=self.th; self.tp.drawOn(c,12,y); y-=5
        y-=self.bh; self.bp.drawOn(c,12,y)

def img(path,w=CW,cap=None):
    from PIL import Image as PILImage
    iw,ih=PILImage.open(path).size
    im=Image(path,width=w,height=w*ih/iw)
    im.hAlign='LEFT'
    return [im]+([Paragraph(cap,ST['cap'])] if cap else [Spacer(1,7)])

def table(header,rows,widths,align=None,head_bg=None,zebra=True,fs=8.2,pad=4.2):
    data=[[Paragraph(str(h),ST['th']) for h in header]]
    for r in rows:
        data.append([x if isinstance(x,Paragraph) else Paragraph(str(x),ST['td']) for x in r])
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    cmds=[('VALIGN',(0,0),(-1,-1),'MIDDLE'),
          ('LINEBELOW',(0,0),(-1,0),0.9,AXIS),
          ('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),
          ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]
    if zebra:
        for i in range(1,len(data)):
            if i%2==0: cmds.append(('BACKGROUND',(0,i),(-1,i),SURF))
        cmds.append(('LINEBELOW',(0,1),(-1,-2),0.4,GRID))
    if align:
        for col,a in align.items(): cmds.append(('ALIGN',(col,0),(col,-1),a))
    t.setStyle(TableStyle(cmds))
    return t

def bullets(items,style='bullet',color=None):
    out=[]
    for it in items:
        out.append(Paragraph(it,ST[style],bulletText='•'))
    return out

def stat_row(items,w=CW):
    """Row of hero figures: [(value, label, color), ...]"""
    n=len(items); cw=w/n
    cells=[]
    for v,l,c in items:
        # each stat is its own one-column table: value row, then label row
        cells.append([[Paragraph(f'<font color="#{c.hexval()[2:]}" size="19"><b>{v}</b></font>',
                                 P('sv',fontSize=19,leading=23))],
                      [Paragraph(l,P('sl',fontSize=8.1,leading=11,textColor=INK2))]])
    t=Table([[Table(c,colWidths=[cw-10],style=TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1)])) for c in cells]],
        colWidths=[cw]*n,hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    return t

class Doc(BaseDocTemplate):
    def __init__(self,path,**kw):
        super().__init__(path,pagesize=A4,leftMargin=ML,rightMargin=MR,
                         topMargin=MT,bottomMargin=MB,title=kw.pop('title',''),
                         author='Demand Planning',**kw)
        fr=Frame(ML,MB,CW,PH-MT-MB,id='n',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        # chrome is drawn at page END so the running head shows the section
        # the page actually contains, not the one that was open when it started
        self.addPageTemplates([PageTemplate(id='cover',frames=[fr],onPage=self._cover),
                               PageTemplate(id='body',frames=[fr],onPageEnd=self._chrome)])
        self.section=''
    def _cover(self,c,d): pass
    def afterFlowable(self,f):
        # the running head must name the section whose heading actually landed
        # on this page, so read it off the flowable rather than a marker
        n=getattr(f,'_sectionName',None)
        if n: self.section=n
    def _chrome(self,c,d):
        c.saveState()
        c.setFont(F,7.6); c.setFillColor(MUTED)
        c.drawString(ML,PH-MT+7,getattr(self,'runningTitle','O9 Scope Analysis'))
        if self.section:
            c.drawRightString(PW-MR,PH-MT+7,self.section)
        c.setStrokeColor(GRID); c.setLineWidth(0.6)
        c.line(ML,PH-MT+3,PW-MR,PH-MT+3)
        c.line(ML,MB-8,PW-MR,MB-8)
        c.setFillColor(MUTED)
        c.drawRightString(PW-MR,MB-16,str(d.page))
        c.drawString(ML,MB-16,getattr(self,'footNote','Closed history through 2026.M07'))
        c.restoreState()

def tag_section(para,name):
    """Mark a heading with the running-header text it should produce."""
    para._sectionName=name
    return para
