# -*- coding: utf-8 -*-
import sys, json; sys.path.insert(0,'analysis/scripts')
from pdfkit import *
from reportlab.platypus import (Spacer, Paragraph, PageBreak, KeepTogether, Table,
    TableStyle, NextPageTemplate)
from reportlab.lib.units import mm
import pandas as pd, numpy as np

J=lambda f: json.load(open(f'analysis/out/{f}'))
s1=J('a1_seasonality.json'); s2=J('a2_epos.json'); s3=J('a3_launch.json')
s4=J('a4.json'); s5=J('a5.json'); s6=J('a6.json'); s7=J('a7.json'); FA=J('facts.json')
CH='analysis/charts/'
M=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
def pct(x,d=0): return f'{x*100:.{d}f}%'
def cumy(k,d=0): return f'{s3["cum_y1"][k]:.{d}f}%'   # already stored 0-100
def u(x): return f'{x:,.0f}'
def K(x): return f'{x/1e3:,.0f}K' if abs(x)<1e6 else f'{x/1e6:.2f}M'

doc=Doc('Scope Analysis Report.pdf',title='O9 Scope Analysis')
E=[]
# Headings carry keepWithNext, so they follow their content to the next page
# instead of stranding at the foot of one.
_sec=['']
def sec(name): _sec[0]=name
def h2(t): E.append(tag_section(Paragraph(t,ST['h2']),_sec[0]))
def h3(t): E.append(Paragraph(t,ST['h3']))
def p(t): E.append(Paragraph(t,ST['body']))
def lead(t): E.append(Paragraph(t,ST['lead']))
def cap(t): E.append(Paragraph(t,ST['cap']))
def sp(h=7): E.append(Spacer(1,h))
FIGW=CW*0.86
def fig(n,c): E.extend(img(CH+n,FIGW,c))
def bl(items): E.extend(bullets(items))
def rule_box(t,b,accent=S1,bg=BANDBLUE): E.append(Callout(t,b,accent,bg)); sp(9)
def softbreak():
    """Section divider that lets content keep flowing, so pages fill instead of
    stranding a two-line tail on a page of its own."""
    sp(10); E.append(HR(CW,AXIS,0.9)); sp(2)

# ============================== COVER ==============================
E.append(Spacer(1,52))
E.append(Paragraph('<font color="#2a78d6"><b>DEMAND PLANNING</b></font>',
                   P('k',fontName=FB,fontSize=9,leading=11,spaceAfter=10)))
E.append(Paragraph('O9 Scope Analysis',P('t',fontName=FB,fontSize=33,leading=37,spaceAfter=6)))
E.append(Paragraph('How your codes behave, and what to do about it',
                   P('s',fontSize=15,leading=20,textColor=INK2,spaceAfter=22)))
E.append(HR(CW,AXIS,1)); E.append(Spacer(1,16))
E.append(stat_row([(f"{FA['pls']}",'product lines',S1),
                   (f"{FA['houses']}",'houses',S1),
                   (K(FA['vol12']),'units shipped, last 12 closed months',S1),
                   (K(FA['fwd']),'units in the forward book',S1)]))
E.append(Spacer(1,4)); E.append(HR(CW,GRID)); E.append(Spacer(1,18))
lead('This report reads your O9 extract the way a demand planner would: it looks for the '
     'patterns that repeat, separates the codes the system can forecast from the ones it '
     'cannot, and turns both into rules you can apply next cycle.')
sp(10)
E.append(Callout('What this report is built on',
  'One O9 extract at product-line and customer-group level, 2022.M03 to 2030.M03, covering ten '
  'measures. History is closed through <b>2026.M07</b>. Every aggregate excludes '
  '<i>Gucci Fragrance Multiline (00003484)</i>, a catch-all line that alone carries 37% of the '
  'volume and would otherwise drown every average; it gets its own appendix.',S1,BANDBLUE))
sp(14)
E.append(Paragraph('Contents',ST['h3']))
toc=[('1','What this data can and cannot tell you'),('2','Executive summary'),
     ('3','The shape of your scope'),('4','The calendar: shipping vs selling'),
     ('5','The three-month rule'),('6','Launches: the front-load and the month-3 trap'),
     ('7','Service: the demand you win and then lose'),('8','Anatomy of the forward book'),
     ('9','ULTA versus everyone else'),('10','House by house'),
     ('11','How to tell a good forecast from a bad one'),('12','Your monthly operating rhythm'),
     ('13','Watchlist: where to spend this month'),('14','Appendices')]
E.append(Table([[Paragraph(f'<font color="#898781">{n}</font>',ST['toc']),
                 Paragraph(t,ST['toc'])] for n,t in toc],
        colWidths=[12*mm,CW-12*mm],hAlign='LEFT',
        style=TableStyle([('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1),
                          ('LEFTPADDING',(0,0),(-1,-1),0)])))
E.append(NextPageTemplate('body'))
E.append(PageBreak())

# ============================== 1. LIMITS ==============================
sec('1 · What the data can tell you')
h2('1 · What this data can and cannot tell you')
lead('Before any conclusion, one structural fact about the extract decides which questions are '
     'answerable and which are not.')
h3('History in O9 is overwritten, so forecast accuracy is not measurable here')
p('In every closed month from 2023.M08 to 2026.M07, three measures are identical to the unit: '
  '<b>System FC - Final = Consensus - Final = Actuals</b>. Not close — identical, in 100% of cells. '
  'O9 has written the actual back over the forecast once each month closed.')
p('That means this extract holds no memory of what you actually predicted before the month happened. '
  'MAPE and BIAS — the two numbers you are measured on — cannot be computed from it, by anyone, at any '
  'level of effort. Any report claiming an accuracy figure from this file would be reporting the '
  'accuracy of actuals against themselves, which is always perfect and always meaningless.')
rule_box('What this changes about the report',
  'Everything here is built on <b>structural evidence</b> instead: how demand actually behaves through '
  'the year, how consumer offtake relates to shipments, how launches decay, where service breaks, and '
  'what shape your forward book is in today. These are the drivers <i>behind</i> MAPE and BIAS, so the '
  'rules in Section 11 are written to move both — they are just not scored here.',S1,BANDBLUE)
h3('To measure accuracy, one more extract is needed')
p('Ask O9 for the same measures as a <b>lag snapshot</b>: the Consensus - Final as it stood at lag-1 '
  '(one month before the month closed) and at lag-3, stored against the actual that followed. With '
  '24 months of that, every MAPE, BIAS and forecast-value-added cut in this report becomes computable, '
  'and the rules in Section 11 become testable instead of reasoned.')
h3('Three smaller limits worth knowing')
bl(['<b>Customer Fcst is completely empty.</b> Not sparse — zero populated cells across the whole '
    'extract, all 202 lines and all 97 months. Either your customers do not submit through this layer '
    'or it was dropped from the extraction. Everywhere this report describes the consensus build, that '
    'layer is genuinely absent.',
    f'<b>EPOS runs one month behind and covers part of the base.</b> It starts in 2024.M07 and ends '
    f'2026.M07. On the lines that carry it, EPOS sums to a median of {pct(s2["coverage"]["50%"])} of '
    'sell-in, so it is not the whole sell-out picture. This report therefore uses EPOS as a '
    '<b>trend and timing signal</b>, never as an absolute level against shipments.',
    f'<b>August 2026 is still invoicing.</b> Actuals show {u(FA["aug_a"])} units against a consensus of '
    f'{u(FA["aug_c"])}. That gap is almost certainly incomplete billing rather than a real miss, so '
    'every calculation here stops at 2026.M07.'])
E.append(PageBreak())

# ============================== 2. EXEC SUMMARY ==============================
sec('2 · Executive summary')
h2('2 · Executive summary')
lead('Eight findings. Each one is expanded later, and each one has an action attached.')

def finding(n,title,body,accent=S1):
    t=Table([[Paragraph(f'<font color="#{accent.hexval()[2:]}"><b>{n}</b></font>',
                        P('fn',fontName=FB,fontSize=15,leading=17)),
              Table([[Paragraph(f'<b>{title}</b>',P('ft',fontName=FB,fontSize=10.2,leading=13.4))],
                     [Paragraph(body,P('fb',fontSize=9.4,leading=13.4,textColor=INK2))]],
                    colWidths=[CW-14*mm],style=TableStyle([
                      ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
                      ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,0),3)]))]],
            colWidths=[14*mm,CW-14*mm],hAlign='LEFT',
            style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
              ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
              ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
              ('LINEBELOW',(0,0),(-1,-1),0.5,GRID)]))
    E.append(t)

finding('01','You ship on the quarter; your consumer buys at Christmas',
  'Sell-in peaks in <b>March, June and September</b> (index 127, 134, 128) and bottoms in November and '
  'December (77). Consumer offtake does the opposite: December EPOS indexes at <b>269</b>, nearly three '
  'times a normal month. Your shipping calendar is driven by quarter-end, not by demand.')
finding('02','Sell-in leads consumer offtake by about three months',
  f'Across {sum(s2["lag_dist"].values())} lines with a usable EPOS signal, the most common lead is '
  f'<b>3 months</b> and the volume-weighted average is {s2["lag_wmean"]:.1f}. This is the single '
  'most useful number in the report: what the consumer does in December was decided by what you shipped '
  'in September.')
finding('03','A launch is 2.7x a normal month, and then it collapses',
  f'Month 0 of a launch carries <b>{cumy("0")} of the entire first year</b> and months 0-2 '
  f'carry {cumy("2")}. {pct(s3["peak"]["M0"],0)} of launches never beat their own first '
  f'month. Steady state settles at about {pct(s3["steady_ratio"],0)} of the launch month.')
finding('04','You run out of stock exactly when the launch starts selling',
  'Supply cuts during a launch sit near <b>1% in months 0-2</b>, then jump to <b>10%, 10%, 9% and 15%</b> '
  'in months 3 to 6 — which is precisely when consumer offtake peaks. You fill the pipe perfectly and '
  'then fail the reorder.',CRIT)
finding('05','Service loss is concentrated and it got worse',
  f'Demand lost to supply cuts went from 3.1% in 2023 to <b>11.9% in 2025</b>. Two houses carry almost '
  f'all of it: Gucci Make up at {pct(s4["cuts_house"]["Gucci Make up"],0)} and Kylie Makeup at '
  f'{pct(s4["cuts_house"]["Kylie Makeup"],0)}. One code alone — Kylie Skin Tint Foundation at ULTA — has '
  'lost 731K units since January 2025.',CRIT)
finding('06','A third of your forward book cannot be traced to any layer',
  'Summing every extracted layer over the cells where a consensus exists leaves <b>33% of the forward '
  'book — 6.7M units — unexplained</b>. Either a consensus layer is missing from the extract or numbers '
  'are being written directly at consensus level, bypassing the layer structure.',SERIOUS)
finding('07','Only 7% of your volume sits on genuinely stable codes',
  f'Five product lines out of 201 profiled are stable and repeatable. <b>{pct(0.307+0.124,0)} of volume '
  'sits in the two lowest forecastability bands</b>, and the median year-on-year repeatability across '
  'the scope is close to zero. For most of your scope, last year is a weak guide.')
finding('08','The forward book is aggressive near-in and hollow later',
  'The remaining months of 2026 are booked at <b>147% of your current run rate</b>, 2027 at 78%, then it '
  'falls to 18% in 2028. Some of that is a genuine planning wall at 2027.M06, but 49 active lines are '
  'booked more than 45% below what they are currently shipping.',SERIOUS)
sp(10)
rule_box('If you change only one thing',
  'Move your reorder attention from the launch month to <b>launch month + 3</b>. That is where consumer '
  'demand peaks, where 10-15% of demand is currently being lost to cuts, and where your forecast has the '
  'least support. Section 6 has the numbers and Section 12 puts it in the monthly rhythm.',CRIT,
  colors.HexColor('#fdefea'))
E.append(PageBreak())

# ============================== 3. SHAPE OF SCOPE ==============================
sec('3 · The shape of your scope')
h2('3 · The shape of your scope')
lead('Before the patterns, the terrain: what you are actually responsible for, and where the weight sits.')
E.append(stat_row([(f"{FA['pl_active']}",'lines shipping in the last 12 months',S1),
                   (f"{FA['n50']}",'lines make up half the volume',S2),
                   (f"{FA['n80']}",'lines make up 80%',S2),
                   (f"{FA['pl_with_epos']}",'lines with an EPOS signal',S1)]))
sp(4)
p(f'Your scope holds <b>{FA["pls"]} product lines</b> across {FA["houses"]} houses and {FA["brands"]} '
  f'brands, split over two customer groups. {FA["single_cfg"]} lines exist in only one customer group; '
  f'{FA["both_cfg"]} appear in both. Of those, {FA["pl_active"]} actually shipped in the last twelve '
  f'closed months — so roughly a third of the catalogue is dormant or not yet launched.')
fig('c13_pareto.png','Ten product lines carry half of everything you ship. Your forecasting effort '
    'should be distributed the same way.')
p(f'Volume over the last twelve closed months was <b>{u(FA["vol12"])} units</b>, down '
  f'{pct(abs(FA["yoy"]),0)} against the twelve months before. The forward book stands at '
  f'{u(FA["fwd"])} units through 2029.M07.')
h3('The five codes that decide your number')
rows=[[Paragraph(f'<b>{k}</b>',ST['td']),u(v),pct(sh,1)] for k,v,sh in FA['top5']]
E.append(table(['Product line','Units, last 12 closed months','% of scope'],rows,
               [CW*0.56,CW*0.26,CW*0.18],align={1:'RIGHT',2:'RIGHT'}))
cap('A miss on any one of these moves your overall number more than a perfect forecast on the bottom '
    'hundred lines combined.')
h3('Volume by house')
hi=s7['house']; hs=sorted(hi,key=lambda h:-hi[h]['vol12'])
rows=[]
for h in hs:
    d=hi[h]
    tcol=GOOD if d['trend']>0 else CRIT
    rows.append([Paragraph(f'<b>{h}</b>',ST['td']),str(d['lines']),u(d['vol12']),
      Paragraph(f'<font color="#{tcol.hexval()[2:]}">{d["trend"]*100:+.0f}%</font>',ST['td']),
      u(d['fwd']),
      Paragraph(f'<font color="#{(CRIT if d["cutrate"]>0.15 else SERIOUS if d["cutrate"]>0.05 else GOOD).hexval()[2:]}">'
                f'{pct(d["cutrate"],1)}</font>',ST['td']),
      ', '.join(m for m,_ in d['peaks'][:3])])
E.append(table(['House','Lines','Units L12M','YoY','Forward book','Demand lost','Peak months'],rows,
    [CW*0.21,CW*0.07,CW*0.14,CW*0.09,CW*0.15,CW*0.12,CW*0.22],
    align={1:'CENTER',2:'RIGHT',3:'RIGHT',4:'RIGHT',5:'RIGHT'}))
cap('Demand lost = supply cuts / (actuals + cuts), 2025.M01-2026.M07. YoY compares the last 12 closed '
    'months to the 12 before.')
p('Two things stand out. <b>Gucci is more than half your volume and the most stable</b> — it is the '
  'base you plan against. <b>Kylie Jenner Fragrances is only six product lines but 12% of volume</b>, '
  'growing, and almost entirely launch-driven: it is the highest-risk block in the scope, and Section 11 '
  'shows it scores lowest on forecastability by a wide margin.')
softbreak()

# ============================== 4. CALENDAR ==============================
sec('4 · The calendar')
h2('4 · The calendar: shipping versus selling')
lead('You asked which months are strongest and where it pays to protect the forecast. The answer is not '
     'one calendar but two, and they do not line up.')
fig('c01_season.png','Two different calendars in one business. Both series are indexed to their own '
    'average month, so they share a single scale.')
h3('Your shipping calendar is a quarter-end calendar')
p('Sell-in peaks in <b>March (127), June (134) and September (128)</b> — the last month of Q1, Q2 and Q3 '
  '— and falls to its floor in <b>November and December (77 and 77)</b>. That is not a consumer pattern. '
  'Consumers do not buy perfume in a rhythm that happens to match fiscal quarters. It is the signature of '
  'quarter-end shipping: orders pulled forward to land inside the closing period.')
h3('Your consumer calendar is a Christmas calendar')
p('EPOS tells the opposite story. December indexes at <b>269</b> and November at 117; every other month '
  'sits below 100. Consumer offtake in December is close to three times a normal month, and it happens in '
  'the two months when your own shipments are at their lowest.')
rule_box('Why both facts are true at once',
  'You are not shipping less in December because demand is weak. You are shipping less because you '
  '<b>already shipped it</b> — in September and October, into retailer inventory, ahead of the season. '
  'The stock that sells on 20 December left your warehouse around 90 days earlier. That is the mechanism '
  'behind every recommendation in this report.',S1,BANDBLUE)
h3('The peaks repeat, which makes them plannable')
fig('c02_yoy.png','The same three peaks appear independently in 2024 and 2025, which is what makes them '
    'safe to build a rule on.')
p('March indexes 125 then 129. June 138 then 130. September 135 then 121. A pattern that reproduces in '
  'two separate years without being fitted to is a pattern you can plan against. The troughs repeat too: '
  'November and December are the two lowest months in both years.')
E.append(Callout('Where to protect the forecast',
  '<b>March, June and September</b> are your three exposure months on the shipping side — they are the '
  'largest, they repeat, and (see Section 7) they are also where you lose the most demand to supply cuts. '
  '<b>October and November</b> are the exposure months for the holiday build: what you fail to ship then '
  'cannot be recovered in December, because December is when the consumer is already buying.',S2,
  colors.HexColor('#fdefea')))
sp(9)
h3('One important caution before you apply this')
p('The aggregate seasonality is real, but it is not universal. Measured line by line, September — the '
  f'most consistent month in the scope — is above its own line median in only <b>'
  f'{pct(s1["month_consistency"]["9"],0)} of cases</b>. March reaches '
  f'{pct(s1["month_consistency"]["3"],0)}. In other words the peaks are driven by a subset of large '
  'codes, not by the catalogue moving together.')
rule_box('Do not apply a blanket seasonal uplift',
  'A flat "+25% in September because September is strong" would be wrong on roughly six lines in ten. '
  'Use the calendar to decide <b>where to look</b>, then confirm the pattern on the individual code '
  'before you move the number. Section 11 gives the test.',WARN,colors.HexColor('#fdf6e3'))
softbreak()

# ============================== 5. THREE-MONTH RULE ==============================
sec('5 · The three-month rule')
h2('5 · The three-month rule')
lead('You asked what relationship EPOS has with the final trend. This is it, and it is the most useful '
     'mechanism in your scope.')
fig('c03_lag.png','For each line, the lag at which shipments best explain later consumer offtake. The '
    'distribution has a clear centre.')
p(f'Testing every product line with a usable EPOS history at lags of zero to four months, <b>3 months is '
  f'the most common answer</b> ({s2["lag_dist"]["3"]} lines), followed by 2 months '
  f'({s2["lag_dist"]["2"]} lines). Weighted by volume the average is '
  f'<b>{s2["lag_wmean"]:.1f} months</b>. At scope level the same test gives its strongest correlation at '
  'exactly three months, r = +0.62.')
rule_box('The three-month rule',
  'EPOS in month <b>T</b> is mostly the consequence of what you shipped in month <b>T-3</b>. Which means '
  'EPOS today is not news about today — it is the <b>scorecard on a decision you made a quarter ago</b>, '
  'and the best available evidence about what you should ship next.',S1,BANDBLUE)
h3('How to actually use it')
bl(['<b>Read EPOS as a verdict, not a forecast input.</b> When you look at EPOS for month T, you are '
    'grading the shipment you made in T-3. If offtake is weak, the pipe is already too full and the '
    'correction belongs in T+1, not T.',
    '<b>Work backwards from the season.</b> December offtake is set by September and October shipments. '
    'If you want to protect Christmas, the decision window is <b>September</b>. By November it is closed.',
    '<b>Watch the gap, not the level.</b> Because EPOS covers only part of the retailer base, its absolute '
    'value tells you little. Its <b>direction against your own shipment direction</b> tells you a great '
    'deal.'])
h3('Where shipments and consumer demand currently disagree')
fig('c16_momentum.png','Each bubble is a product line. Above the dashed line, you are shipping faster '
    'than the consumer is buying.')
p(f'Comparing the last six closed months against the six before, sell-in growth and EPOS growth correlate '
  f'at only <b>r = +{s2["mom_corr"]:.2f}</b> — a weak relationship. In a healthy book these two move '
  f'together. <b>{s2["over_n"]} lines are growing shipments more than 25 points faster than consumer '
  f'offtake</b>; those units are going into retailer inventory, not into consumers\' hands. '
  f'{s2["under_n"]} lines are the reverse.')
D=pd.read_csv('analysis/out/a2_momentum.csv')
top=D.nlargest(7,'gap')
rows=[[Paragraph(f"<b>{r.PL}</b>",ST['td']),r.CFG.replace('P_US_',''),
       Paragraph(f'<font color="#{CRIT.hexval()[2:]}">{r.sellin_g*100:+.0f}%</font>',ST['td']),
       Paragraph(f'<font color="#{S1.hexval()[2:]}">{r.epos_g*100:+.0f}%</font>',ST['td']),
       f'{r.gap*100:+.0f} pp'] for r in top.itertuples()]
E.append(table(['Product line','Group','Sell-in growth','EPOS growth','Gap'],rows,
    [CW*0.38,CW*0.16,CW*0.16,CW*0.15,CW*0.15],align={2:'RIGHT',3:'RIGHT',4:'RIGHT'}))
cap('Last 6 closed months vs the 6 before. A large positive gap means shipments are outrunning consumer '
    'offtake — the classic setup for a cut-back three to six months later.')
rule_box('The inventory-build warning sign',
  'When sell-in is growing and EPOS is falling on the same code for two consecutive months, you are '
  'filling the retailer, not the consumer. Historically this is followed by an order stop. <b>Hold the '
  'forecast flat rather than extrapolating the shipment trend</b> — the shipment trend is the problem, '
  'not the signal.',CRIT,colors.HexColor('#fdefea'))
softbreak()

# ============================== 6. LAUNCHES ==============================
sec('6 · Launches')
h2('6 · Launches: the front-load and the month-3 trap')
lead(f'Your instinct that launch volume is very strong is correct, and the data lets us put exact numbers '
     f'on it. This section is built on {s3["n_launches"]} genuine launches since 2023.M09.')
E.append(stat_row([(f'{s3["m0_multiple"]:.1f}x','month 0 vs an average month of year 1',S2),
                   (cumy("0"),'of year-1 volume lands in month 0',S2),
                   (cumy("2"),'lands in the first three months',S2),
                   (pct(s3["steady_ratio"],0),'is where it settles',S1)]))
sp(4)
fig('c04_launch.png','Every launch aligned on its first shipment month. The front-load is severe and it '
    'is over quickly.')
p(f'A launch month is <b>{s3["m0_multiple"]:.1f} times</b> an average month of that product\'s first '
  f'year. Almost a quarter of the entire first year ships in month 0 alone, '
  f'{cumy("2")} in the first three months, and {cumy("5")} in the first '
  f'six. By month 6 to 11 the code has settled at roughly <b>{pct(s3["steady_ratio"],0)} of its launch '
  f'month</b>.')
p(f'The single most useful fact for forecasting: <b>{pct(s3["peak"]["M0"],0)} of launches never exceed '
  f'their own first month</b>, and {pct(s3["peak"]["M0_M1"],0)} peak in month 0 or 1. A launch curve '
  'that projects growth after month 1 is fighting the base rate.')
rule_box('Launch rule of thumb',
  'Plan the pipe fill, then plan the cliff. If you know the month-0 order, a defensible first pass is: '
  '<b>month 1-2 at roughly half of month 0 combined, and a steady state near one fifth of month 0 from '
  'month 6</b>. Then adjust with the EPOS read described below — not with optimism.',S1,BANDBLUE)
h3('The consumer arrives three months after you ship')
fig('c05_launch_epos.png','The same three-month lag from Section 5, visible inside every launch.')
p('Sell-in peaks in month 0. Consumer offtake peaks in <b>month 3</b>. Between them sits a window where '
  'the retailer is holding your entire pipe fill and the consumer has barely started. That window is '
  'where launch forecasts are usually judged — and judged too early.')
E.append(Callout('The first real read on a launch is month 3, not month 1',
  'Month 1 and 2 EPOS tells you almost nothing: the product is still landing on shelf. <b>Month 3 EPOS '
  'is your first honest signal</b> of whether the launch works. Resist re-forecasting the full year on '
  'month-1 data in either direction.',S1,BANDBLUE))
sp(9)
h3('And that is exactly where service fails')
fig('c06_launch_cuts.png','Demand lost to supply cuts, by month of the launch. Months 0-2 are near '
    'perfect; months 3-6 are not.')
p('This is the most actionable finding in the report. During months 0 to 2 of a launch, demand lost to '
  'supply cuts sits at <b>0.2%, 0.9% and 1.1%</b> — essentially perfect service. Then it jumps to '
  '<b>9.5% in month 3, 10.1% in month 4, 9.0% in month 5 and 14.6% in month 6</b>.')
p('The pipe fill is planned, built and shipped beautifully. The <b>reorder is not</b>. And the reorder '
  'falls precisely in months 3 to 6 — the months where, as the chart above shows, the consumer is buying '
  'hardest. You lose the demand at the exact moment you finally earned it.')
rule_box('The month-3 trap',
  'A launch does not fail in month 0. It fails in month 3, when consumer demand arrives, the retailer '
  'reorders, and there is no stock. <b>Build the month 3-6 replenishment into the launch plan from the '
  'start</b>, and treat a launch as unfinished until month 6 rather than closing it after the pipe fill '
  'ships.',CRIT,colors.HexColor('#fdefea'))
h3('When you launch')
lm=s3['launch_months']
p('Launches cluster heavily in the second half of the year — '
  + ', '.join(f'<b>{m}</b> ({lm[m]})' for m in ['Jun','Jul','Sep','Oct','Nov','Dec'] if m in lm)
  + '. Combined with the three-month lag, an October launch has its consumer peak in January and its '
    'reorder risk window across the exact months when the rest of the portfolio is also fighting for '
    'supply. That collision is visible in the next section.')
softbreak()

# ============================== 7. SERVICE ==============================
sec('7 · Service')
h2('7 · Service: the demand you win and then lose')
lead('Supply cuts are demand you already earned and could not deliver. In this scope they have grown '
     'into the single largest correctable loss.')
cy={r['year']:r for r in s4['cuts_year']}
E.append(stat_row([(pct(cy['2023']['rate'],1),'demand lost, 2023',GOOD),
                   (pct(cy['2024']['rate'],1),'2024',WARN),
                   (pct(cy['2025']['rate'],1),'2025',CRIT),
                   (pct(cy['2026']['rate'],1),'2026 to date',SERIOUS)]))
sp(4)
p(f'Demand lost to supply cuts went from <b>3.1% in 2023 to 11.9% in 2025</b> — nearly four times worse '
  f'in two years — before improving to {pct(cy["2026"]["rate"],1)} in 2026 to date. In the last twelve '
  f'closed months alone, <b>{u(FA["cuts12"])} units</b> of demand were ordered and not delivered.')
h3('You run out of stock in your own peak months')
fig('c07_cuts_month.png','Demand lost by calendar month. Compare against the sell-in peaks from Section 4.')
p('March 10.1%. September 11.0%. October 10.7%. November 11.0%. Set these against the shipping calendar: '
  '<b>March and September are two of your three biggest sell-in months</b>, and October-November is the '
  'holiday build. The months where you most need supply are the months where you most often fail to have it.')
p('The two clean months are May (4.2%) and June (3.9%) — and June is your single largest sell-in month. '
  'So this is not a pure capacity ceiling; it is a planning and phasing problem. When supply knows the '
  'peak is coming, it delivers.')
rule_box('The forecast consequence',
  'A supply cut corrupts your history. The actual you record in a cut month is <b>not demand — it is '
  'what supply allowed</b>. The system then learns that suppressed number as the new baseline and '
  'forecasts the following year down from it. Every cut month is a month where the algorithm is being '
  'taught the wrong lesson, which is why Section 11 asks you to check cuts before trusting any System FC '
  'that looks low.',CRIT,colors.HexColor('#fdefea'))
h3('Where it is concentrated')
fig('c08_cuts_house.png','Service loss by house. Two houses carry nearly all of it.')
CL=pd.read_csv('analysis/out/a4_cutlines.csv')
rows=[[Paragraph(f'<b>{r.PL}</b>',ST['td']),r.CFG.replace('P_US_',''),u(r.actuals),u(r.cuts),
       Paragraph(f'<font color="#{(CRIT if r.rate>0.4 else SERIOUS).hexval()[2:]}"><b>{pct(r.rate,0)}</b></font>',ST['td'])]
      for r in CL.head(10).itertuples()]
E.append(table(['Product line','Group','Units delivered','Units lost','Demand lost'],rows,
    [CW*0.36,CW*0.16,CW*0.17,CW*0.15,CW*0.16],align={2:'RIGHT',3:'RIGHT',4:'RIGHT'}))
cap('2025.M01-2026.M07, ranked by units lost.')
p('<b>Kylie Skin Tint Foundation at ULTA is the worst single problem in your scope.</b> It lost 731K '
  'units against 746K delivered since January 2025 — a 49.5% cut rate. Effectively, for every unit that '
  'reached the customer, another was ordered and refused. Six of the top ten are Gucci Make up colour '
  'codes running cut rates between 30% and 67%, which is a category-level supply issue rather than ten '
  'separate incidents.')
h3('A small but telling detail')
p(f'There are <b>{s4["cuts_nofcst"]["n"]} line-months carrying supply cuts against a consensus of zero</b> '
  f'({u(s4["cuts_nofcst"]["units"])} units). The customer ordered something you had forecast at nothing. '
  'The volume is trivial; the signal is not. Those are codes the planning process had already written off '
  'while the customer had not.')
softbreak()

# ============================== 8. FORWARD BOOK ==============================
sec('8 · The forward book')
h2('8 · Anatomy of the forward book')
lead(f'What you are currently promising supply: {u(s4["fwd_total"])} units between 2026.M08 and 2029.M07, '
     f'and how it was built.')
fig('c10_layers.png','Every layer measured over the cells where a consensus exists, so the residual is real.')
h3('One third of the book has no visible origin')
p('System FC contributes 40.8% of the forward consensus. Initiative Forecast adds 13.5%, Total Demand '
  'Assumption 10.7%, Prometheus 6.0%, and Reasonability Adjustment removes 4.1%. That accounts for 67%. '
  'The remaining <b>33% — 6.7 million units — does not reconcile to any layer in this extract</b>.')
p('The residual is concentrated, not spread thin. It sits on a handful of large codes: Gucci Guilty PH '
  'Eau de Parfum (+1.25M), Kylie Jenner Mood Stones (+1.07M), Gorgeous Gardenia (+836K) and Gucci Flora '
  'Gorgeous Orchid Intense (+794K). Several of these are also flagged in Section 13 as over-booked.')
rule_box('Worth resolving before the next cycle',
  'Either a consensus layer was not included in the extraction, or numbers are being written straight at '
  'consensus level and bypassing the layer structure. <b>The distinction matters</b>: if it is the second, '
  'a third of what you send supply has no owner, no stated assumption, and no audit trail — and it is '
  'sitting on your largest codes.',SERIOUS,colors.HexColor('#fdf6e3'))
h3('Your manual layers pull in a consistent direction')
ra=s4['dir_Rea']; td=s4['dir_Tot']
p(f'<b>Reasonability Adjustment is negative {pct(ra["neg"],0)} of the time</b>, with a net effect of '
  f'{u(ra["net"])} units across the extract. Read plainly: when your team overrides the system, they '
  f'almost always override it <b>downwards</b>. That is a standing, collective judgement that System FC '
  f'runs hot.')
p(f'Total Demand Assumption is more balanced ({pct(td["neg"],0)} negative) and nets positive at '
  f'+{u(td["net"])} units, which fits its purpose — carrying market insight in both directions rather '
  f'than correcting a bias.')
E.append(Callout('This is the closest thing to a bias measurement available here',
  'You cannot compute BIAS without forecast snapshots. But a Reasonability Adjustment layer that is '
  'negative seven times out of ten is your own organisation telling you, cycle after cycle, that the '
  'system over-forecasts. When the lag snapshots arrive, <b>test that hypothesis first</b> — and if it '
  'holds, the fix belongs in the system parameters, not in a manual correction repeated every month.',
  S1,BANDBLUE))
sp(9)
h3('Aggressive near-in, hollow later')
fig('c09_fwdbook.png','Average monthly consensus by year against the current run rate.')
p('The remaining months of 2026 are booked at <b>147% of the last twelve months\' run rate</b>, 2027 at '
  '78%, 2028 at 18% and 2029 at 13%.')
p('The collapse after 2027 is largely structural rather than a planning failure: <b>90 lines end at '
  '2027.M06 and 58 end at 2029.M07</b>, which are planning-horizon walls, not judgements about those '
  'products. Once those are set aside, only <b>8 active lines</b> stop well before the wall — those are '
  'listed in Section 13.')
p('The near-in figure deserves more attention. Being booked 47% above your run rate for the rest of 2026 '
  'is defensible if it is carried by launches and by the Sep-Nov holiday build — which it partly is. But '
  '15 lines are booked more than 60% above their own trailing twelve months, and Section 13 names them.')
h3('The Prometheus and Total Demand Assumption offset')
p(f'You confirmed this is a known workflow, and it is visible in <b>{s4["offset"]["n"]} line-months</b> '
  f'where Prometheus loads a gross figure and Total Demand Assumption nets it back down — '
  f'{u(s4["offset"]["units"])} units of gross loading. Because the two cancel, this report reads them in '
  'net terms throughout. Worth noting only because those gross numbers are large enough to badly distort '
  'any layer-level reporting that does not net them.')
softbreak()

# ============================== 9. CFG ==============================
sec('9 · ULTA vs everyone else')
h2('9 · ULTA versus everyone else')
lead('You normally combine the two customer groups. On several dimensions they behave differently enough '
     'that combining them hides the pattern.')
cf=s7['cfg']; U=cf['P_US_ULTA']; O=cf['P_US_ALL_OTHERS']
rows=[
 ['Active lines',str(U['lines']),str(O['lines'])],
 ['Volume, last 12 closed months',u(U['vol12']),u(O['vol12'])],
 ['Share of scope',pct(U['share'],0),pct(O['share'],0)],
 ['Forward book',u(U['fwd']),u(O['fwd'])],
 [Paragraph('<b>Demand lost to supply cuts</b>',ST['td']),
  Paragraph(f'<font color="#{CRIT.hexval()[2:]}"><b>{pct(U["cutrate"],1)}</b></font>',ST['td']),
  Paragraph(f'<font color="#{SERIOUS.hexval()[2:]}">{pct(O["cutrate"],1)}</font>',ST['td'])],
 ['Median line volatility (CV)',f'{U["cv"]:.2f}',f'{O["cv"]:.2f}'],
 ['Median months with a shipment',pct(U['active'],0),pct(O['active'],0)],
 ['EPOS coverage of sell-in',pct(s7['epos_quality']['P_US_ULTA']['coverage'],0),
  pct(s7['epos_quality']['P_US_ALL_OTHERS']['coverage'],0)],
 ['Lines carrying an EPOS signal',pct(s7['epos_quality']['P_US_ULTA']['pct_with_epos'],0),
  pct(s7['epos_quality']['P_US_ALL_OTHERS']['pct_with_epos'],0)],
 ['Median forecastability score',f"{s6['cfg']['P_US_ULTA']:.0f}",f"{s6['cfg']['P_US_ALL_OTHERS']:.0f}"],
]
E.append(table(['','P_US_ULTA','P_US_ALL_OTHERS'],rows,[CW*0.46,CW*0.27,CW*0.27],
               align={1:'RIGHT',2:'RIGHT'}))
sp(8)
h3('Three differences that should change how you work them')
bl([f'<b>ULTA loses more than twice as much demand to supply cuts</b> — {pct(U["cutrate"],1)} against '
    f'{pct(O["cutrate"],1)}. On 43% of the volume, ULTA accounts for roughly two thirds of all units '
    'lost. Any service recovery plan should start there.',
    f'<b>ULTA lines ship in fewer months.</b> The median ULTA line has a shipment in only '
    f'{pct(U["active"],0)} of months against {pct(O["active"],0)} for the rest. That is a bigger-drop, '
    'less-frequent order pattern, which raises volatility even when annual demand is identical.',
    f'<b>ULTA has the better EPOS signal.</b> {pct(s7["epos_quality"]["P_US_ULTA"]["coverage"],0)} '
    'coverage against '
    f'{pct(s7["epos_quality"]["P_US_ALL_OTHERS"]["coverage"],0)}, and a stronger three-month correlation '
    '(r = +0.56 vs +0.45). Where you have the clearest view of the consumer, you also have the worst '
    'service — that combination is fixable.'])
h3('They do not peak in the same months')
fig('c14_cfg.png','Sell-in seasonal index by customer group. The peaks differ by a month or more.')
p('ULTA concentrates in <b>June (148), September (149) and May (130)</b>, and is weak in July and August '
  '(72 and 67). Everyone else peaks in <b>March (138)</b> and June (126) with a much flatter profile. '
  'February is the clearest divergence: ULTA indexes 121 while the rest sit at 77.')
p('On the sell-out side both groups spike in December, but with different intensity — ALL_OTHERS reaches '
  'an index of 311 against ULTA\'s 230. ULTA\'s consumer demand is more spread across the year, which '
  'again makes its shipping lumpiness look self-inflicted rather than demand-driven.')
rule_box('Practical consequence',
  'Keep aggregating the two groups for volume reporting, but <b>split them whenever you touch phasing, '
  'service or the holiday build</b>. A single blended seasonal profile will be wrong for both — it will '
  'under-call ULTA in June and September, and over-call it in February for the rest.',S1,BANDBLUE)
softbreak()

# ============================== 10. HOUSES ==============================
sec('10 · House by house')
h2('10 · House by house')
lead('The scope-level calendar is an average of five very different businesses.')
fig('c12_heatmap.png','Sell-in seasonal index by house. Read across each row: 100 is that house\'s own '
    'average month.')
prof={
 'Gucci':('Your base. Plan the rest around it.',
   'Over half your volume and by far the flattest profile — its peaks (Jun 134, Mar 117, Sep 115) are '
   'mild by comparison with every other house. It is also your deepest history and your most repeatable. '
   'Volume is down 11% year on year, and service loss at 4.5% is your second-best. <b>Treat Gucci as the '
   'reference: if a pattern does not show up here, be careful about generalising it.</b>',S1),
 'Kylie Makeup':('Highest service loss, second-highest volume.',
   'A September (150) and June (147) business with a February secondary peak. It carries <b>22.6% demand '
   'lost to supply cuts</b> — the worst in the scope alongside Gucci Make up — and five of the ten worst '
   'service codes. Volume down 14% year on year, but the forward book is 7.4M units, more than double '
   'the trailing year. <b>Service is the whole story here; the forecast is not the constraint, supply '
   'is.</b>',CRIT),
 'Kylie Jenner Fragrances':('Six lines, 12% of volume, the least predictable block you own.',
   'Peaks in March (184) and May (166) and effectively disappears in July and August (25 and 16). Growing '
   '12% year on year with excellent service (0.6% lost). But its median forecastability score is '
   '<b>10 out of 100</b>, far below every other house, because almost everything in it is a recent '
   'launch. <b>This is where judgement matters most and where the system helps least.</b>',SERIOUS),
 'Gucci Make up':('Small volume, disproportionate pain.',
   'A March (182) and September (152) business, down 34% year on year — the steepest decline in the '
   'scope — while losing <b>26.6% of demand to supply cuts</b>, the worst rate of any house. Six of the '
   'ten worst service codes are here. <b>The decline and the service failure are hard to separate: you '
   'cannot tell how much of the 34% is lost demand rather than lost interest.</b>',CRIT),
 'Burberry Make up':('Tiny, but the sharpest seasonality in the scope.',
   'Only 127K units, yet the most extreme calendar you have: <b>October 398 and November 264</b> against '
   'near-zero in January, February, May, June and July. Growing 60% year on year with essentially no '
   'service loss. <b>A pure holiday-gifting profile — forecast it as an event, not as a monthly series.</b>',
   S3),
}
for h in sorted(s7['house'],key=lambda x:-s7['house'][x]['vol12']):
    d=s7['house'][h]; t,body,col=prof[h]
    E.append(KeepTogether([
      Paragraph(f'{h}',ST['h3']),
      Paragraph(f'<font color="#{col.hexval()[2:]}"><b>{t}</b></font>',
                P('pt',fontSize=9.6,leading=13,spaceAfter=4)),
      Table([[Paragraph(f'<b>{u(d["vol12"])}</b><br/><font size="7.6" color="#52514e">units L12M</font>',ST['td']),
              Paragraph(f'<b>{d["trend"]*100:+.0f}%</b><br/><font size="7.6" color="#52514e">year on year</font>',ST['td']),
              Paragraph(f'<b>{u(d["fwd"])}</b><br/><font size="7.6" color="#52514e">forward book</font>',ST['td']),
              Paragraph(f'<b>{pct(d["cutrate"],1)}</b><br/><font size="7.6" color="#52514e">demand lost</font>',ST['td']),
              Paragraph(f'<b>{", ".join(m for m,_ in d["peaks"][:3])}</b><br/><font size="7.6" color="#52514e">peak months</font>',ST['td'])]],
            colWidths=[CW*0.19]*4+[CW*0.24],hAlign='LEFT',
            style=TableStyle([('BACKGROUND',(0,0),(-1,-1),BAND),
              ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
              ('LEFTPADDING',(0,0),(-1,-1),7),('VALIGN',(0,0),(-1,-1),'MIDDLE')])),
      Spacer(1,5),
      Paragraph(body,ST['body']),Spacer(1,4)]))
softbreak()

# ============================== 11. GOOD FORECAST ==============================
sec('11 · Telling a good forecast from a bad one')
h2('11 · How to tell a good forecast from a bad one')
lead('This is the section you asked for: what pattern to look for, and how to know in advance whether a '
     'number is likely to hold.')
h3('Start by accepting that most of your scope is not stable')
fig('c11_arch.png','Every profiled line sorted into a behaviour type. CV is month-to-month volatility.')
su=s6['summary']
p(f'Of 201 product lines profiled, only <b>{su["STABLE & REPEATABLE"]["n"]} are genuinely stable and '
  f'repeatable</b> — {pct(su["STABLE & REPEATABLE"]["vol_sh"],0)} of volume. The largest single group is '
  f'<b>lumpy and event-driven</b>: {su["LUMPY / EVENT-DRIVEN"]["n"]} lines, '
  f'{pct(su["LUMPY / EVENT-DRIVEN"]["vol_sh"],0)} of volume, with a median volatility of '
  f'{su["LUMPY / EVENT-DRIVEN"]["cv"]:.2f} — meaning a typical month deviates from the average by more '
  'than the average itself.')
p('The number that should shape your expectations most: <b>median year-on-year repeatability across the '
  'scope is essentially zero</b>. Only the stable group (0.40) and the declining group (0.24) show any '
  'real correlation between one year\'s monthly shape and the next. For the bulk of your codes, '
  '<i>"what did we do last year"</i> is a weak starting point, and a statistical model fed on it will be '
  'confidently wrong.')
rows=[]
lbl={'STABLE & REPEATABLE':('Stable & repeatable','Trust the system. Review quarterly, not monthly.',GOOD),
     'MODERATE':('Moderate','System plus a seasonal sanity check. Your best effort-to-return ratio.',S1),
     'DECLINING':('Declining','System will lag the decline. Check the EPOS trend before accepting it.',S4),
     'LUMPY / EVENT-DRIVEN':('Lumpy / event-driven','Forecast the events, not the months. Never smooth.',SERIOUS),
     'NEW / LAUNCH':('New / launch','Use the launch curve in Section 6. The system has nothing to learn from.',CRIT),
     'INTERMITTENT':('Intermittent','Do not forecast monthly. Forecast an annual number and let it phase.',MUTED)}
for k in ['STABLE & REPEATABLE','MODERATE','DECLINING','LUMPY / EVENT-DRIVEN','NEW / LAUNCH','INTERMITTENT']:
    d=su[k]; n,how,c=lbl[k]
    rows.append([Paragraph(f'<font color="#{c.hexval()[2:]}"><b>{n}</b></font>',ST['td']),
                 str(d['n']),pct(d['vol_sh'],0),f'{d["cv"]:.2f}',
                 f'{d["repeat"]:+.2f}' if d['repeat'] is not None else '—',
                 Paragraph(how,ST['tdm'])])
E.append(table(['Behaviour type','Lines','% vol','Volatility','YoY repeat','How to forecast it'],rows,
    [CW*0.19,CW*0.07,CW*0.07,CW*0.10,CW*0.11,CW*0.46],align={1:'CENTER',2:'RIGHT',3:'RIGHT',4:'RIGHT'}))
cap('Volatility = coefficient of variation of monthly sell-in. YoY repeat = correlation between this '
    'year\'s monthly shape and last year\'s; above +0.3 means last year is genuinely informative.')
softbreak()
h3('The forecastability score')
p('Combining five things a planner can check before touching a number — volatility, how many months the '
  'code actually ships, whether last year repeats, how much history exists, and whether EPOS is '
  'available — gives a score out of 100 for every line.')
fig('c17_bands.png','Volume by forecastability band. Nearly half your volume sits where the system '
    'cannot carry the forecast alone.')
bd=s6['bands']
rows=[
 [Paragraph(f'<font color="#{GOOD.hexval()[2:]}"><b>HIGH (80-100)</b></font>',ST['td']),
  str(bd['HIGH']['n']),pct(bd['HIGH']['sh'],0),
  Paragraph('Let System FC run. Intervene only when EPOS contradicts it two months running.',ST['tdm'])],
 [Paragraph(f'<font color="#{S1.hexval()[2:]}"><b>GOOD (60-79)</b></font>',ST['td']),
  str(bd['GOOD']['n']),pct(bd['GOOD']['sh'],0),
  Paragraph('System FC plus a seasonal check against the house calendar in Section 10.',ST['tdm'])],
 [Paragraph(f'<font color="#{WARN.hexval()[2:]}"><b>FAIR (40-59)</b></font>',ST['td']),
  str(bd['FAIR']['n']),pct(bd['FAIR']['sh'],0),
  Paragraph('Do not accept the system unreviewed. Anchor on an annual number and phase it deliberately.',ST['tdm'])],
 [Paragraph(f'<font color="#{CRIT.hexval()[2:]}"><b>LOW (0-39)</b></font>',ST['td']),
  str(bd['LOW']['n']),pct(bd['LOW']['sh'],0),
  Paragraph('Manual ownership. The system has no usable pattern here; a machine number is false comfort.',ST['tdm'])]]
E.append(table(['Band','Lines','% of volume','What it means for how you work the code'],rows,
    [CW*0.18,CW*0.08,CW*0.13,CW*0.61],align={1:'CENTER',2:'RIGHT'}))
sp(9)
E.append(Callout('The uncomfortable headline',
  f'<b>{pct(bd["LOW"]["sh"]+bd["FAIR"]["sh"],0)} of your volume sits in the FAIR and LOW bands.</b> That '
  'is not a failing of the system — it is the nature of a launch-heavy beauty portfolio. But it does mean '
  'the majority of your accuracy will be won or lost by judgement on a manageable number of codes, not '
  'by tuning the algorithm.',S1,BANDBLUE))
sp(9)
h3('The seven-point check')
p('Before you accept or move any number, run these in order. They are ordered by how often they catch '
  'something in this scope.')
checks=[
 ('1','Is there a supply cut in the recent history?',
  'If yes, the actual is not demand and the system has learned a suppressed baseline. Correct upward to '
  'true demand before judging the forecast. This is the most frequent trap in your scope — 12% of demand '
  'was lost in 2025.'),
 ('2','What is the EPOS direction over the last three months?',
  'Rising EPOS with flat shipments means upside. Falling EPOS with rising shipments means you are filling '
  'inventory and a cut-back is coming. Remember EPOS reflects what you shipped three months ago.'),
 ('3','Is this code within six months of launch?',
  f'If yes, ignore the statistical trend entirely and use the launch curve: month 0 is '
  f'{cumy("0")} of year one, settling near {pct(s3["steady_ratio"],0)} of month 0. Watch '
  'month 3 for the first honest consumer read.'),
 ('4','Does the monthly shape repeat from last year?',
  'Check the same months a year ago. If the shape repeats, seasonality is real and you can lean on it. '
  'If it does not — the case for most of your scope — do not apply a seasonal factor at all.'),
 ('5','How many months of the year does this code actually ship?',
  'Below about 50%, monthly forecasting is the wrong tool. Set an annual volume and let phasing follow '
  'the order pattern rather than a smooth curve.'),
 ('6','Is the forward number consistent with the trailing twelve months?',
  'A code booked at more than 1.6x or less than 0.55x its own trailing year needs a stated reason — a '
  'launch, a delisting, a known promotion. If nobody can name the reason, the number is wrong.'),
 ('7','Is the peak month protected on the supply side?',
  'March, June and September for shipping; October and November for the holiday build. A forecast that '
  'is right but unserved scores the same as a forecast that is wrong.'),
]
for n,q,a in checks:
    E.append(KeepTogether([
      Table([[Paragraph(f'<font color="#2a78d6"><b>{n}</b></font>',P('cn',fontName=FB,fontSize=12,leading=15)),
              Table([[Paragraph(f'<b>{q}</b>',P('cq',fontName=FB,fontSize=9.5,leading=12.8))],
                     [Paragraph(a,P('ca',fontSize=9.2,leading=13,textColor=INK2))]],
                    colWidths=[CW-11*mm],style=TableStyle([
                      ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
                      ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(0,0),2)]))]],
            colWidths=[11*mm,CW-11*mm],hAlign='LEFT',
            style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
              ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
              ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
              ('LINEBELOW',(0,0),(-1,-1),0.5,GRID)]))]))
sp(10)
h3('What "a good forecast" looks like in this scope')
rule_box('The signature of a number you can trust',
  'It sits on a code with a repeating monthly shape and history longer than two years; its EPOS trend '
  'points the same way as its shipment trend; it is inside 0.6x to 1.6x of the trailing twelve months '
  'unless someone can name the event; its recent actuals are not contaminated by supply cuts; and its '
  'peak month has supply behind it. <b>When all five hold, leave it alone. When two or more fail, the '
  'number needs a person, not a re-run.</b>',GOOD,colors.HexColor('#eef7ee'))
softbreak()

# ============================== 12. RHYTHM ==============================
sec('12 · Monthly operating rhythm')
h2('12 · Your monthly operating rhythm')
lead('The findings turned into a calendar. Each month has one thing that matters more than the rest, '
     'derived from the three-month lag and your own seasonality.')
cal=[
 ('Jan','Read the holiday verdict','Post-season EPOS is in. Compare December offtake against the Sep-Oct '
  'shipments that created it; that ratio is your single best read on retailer inventory entering the year.',S1),
 ('Feb','ULTA secondary peak','ULTA indexes 121 while the rest of the scope sits at 77. Do not let a '
  'blended profile flatten it.',S1),
 ('Mar','Peak month — protect it','Index 127 and 10.1% of demand historically lost to cuts. Confirm '
  'supply on the top ten codes before the month opens.',CRIT),
 ('Apr','Clean-up month','Low volume, low risk. The right month to fix master data, close horizon cliffs '
  'and review the codes flagged in Section 13.',GOOD),
 ('May','Build the June plan','June is your largest month; May is when it is still changeable. ULTA '
  'indexes 130 here.',S1),
 ('Jun','Largest month of the year','Index 134 and your best service month (3.9%). Proof that supply '
  'performs when the peak is anticipated — use it as the benchmark for March and September.',S4),
 ('Jul','Trough — start the holiday build','Kylie Jenner Fragrances effectively stops (index 25). This is '
  'the decision point for December: what ships from September lands with the consumer at Christmas.',S2),
 ('Aug','Lock the holiday supply','Last month to influence the Sep-Nov build with lead time in hand. '
  '9.5% of demand lost historically.',S2),
 ('Sep','The most important month','Index 128, the most consistent peak in the scope, 11.0% demand lost, '
  'and the shipments that create December offtake. If you protect one month, protect this one.',CRIT),
 ('Oct','Holiday build continues','Index 98 but 10.7% demand lost, and Burberry peaks at 398. Watch '
  'service, not volume.',CRIT),
 ('Nov','Last shipping window','Index 77 and 11.0% lost. What is not shipped now cannot reach the '
  'consumer for Christmas.',CRIT),
 ('Dec','Consumer peak, shipping trough','EPOS index 269 against a sell-in index of 77. Nothing you do to '
  'the forecast now changes December — read it, and carry the read into next September.',S1),
]
for m,t,b,c in cal:
    E.append(Table([[
      Paragraph(f'<font color="#{c.hexval()[2:]}"><b>{m}</b></font>',
                P('cm',fontName=FB,fontSize=11,leading=14)),
      Table([[Paragraph(f'<b>{t}</b>',P('ct2',fontName=FB,fontSize=9.4,leading=12.4))],
             [Paragraph(b,P('cb2',fontSize=9.1,leading=12.8,textColor=INK2))]],
            colWidths=[CW-16*mm],style=TableStyle([
              ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
              ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(0,0),2)]))]],
      colWidths=[16*mm,CW-16*mm],hAlign='LEFT',
      style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),5.5),('BOTTOMPADDING',(0,0),(-1,-1),5.5),
        ('LINEBELOW',(0,0),(-1,-1),0.5,GRID)])))
sp(10)
rule_box('The rhythm in one line',
  'September decides December. June proves supply can perform. March and September are where you lose '
  'demand you already won. Everything else is maintenance.',S1,BANDBLUE)
softbreak()

# ============================== 13. WATCHLIST ==============================
sec('13 · Watchlist')
h2('13 · Watchlist: where to spend this month')
lead('Seven automated checks run against the forward book as it stands. A line can appear under more '
     'than one flag.')
fig('c15_watchlist.png','Volume carried by each flag. Not all flags are equally urgent — the table below '
    'gives the priority order.')
prio=[
 ('SERVICE-LOSS','Losing more than 20% of demand to supply cuts',CRIT,
  'Highest return in the scope. This is demand already won.'),
 ('LOST-FORECAST','Selling now, but the next 12 months are effectively empty',CRIT,
  'Supply is not being told about volume you are still shipping.'),
 ('CONSUMER-DECLINE','EPOS down more than 25% while the forward book is held flat or up',CRIT,
  'The classic over-forecast setup; correct before it becomes a write-off.'),
 ('OVER-BOOKED','Booked more than 60% above the trailing twelve months',SERIOUS,
  'Defensible only with a named launch or event behind it.'),
 ('UNDER-BOOKED','Booked more than 45% below the trailing twelve months',SERIOUS,
  'Largest group by volume. Some is genuine decline; verify code by code.'),
 ('HORIZON-CLIFF','Active line whose forecast stops well before the 2027.M06 wall',WARN,
  'Usually a maintenance gap rather than a judgement.'),
 ('PHANTOM-FORECAST','A forward book on a line that has stopped selling',WARN,
  'Small volume, but it inflates what you promise supply.'),
]
rows=[]
for k,d,c,why in prio:
    f=s5[k]
    rows.append([Paragraph(f'<font color="#{c.hexval()[2:]}"><b>{k.replace("-"," ").title()}</b></font>',ST['td']),
                 str(f['n']),K(f['vol']),Paragraph(d,ST['tdm'])])
E.append(table(['Flag','Lines','Units at stake','What it means'],rows,
    [CW*0.21,CW*0.08,CW*0.14,CW*0.57],align={1:'CENTER',2:'RIGHT'}))
cap('Units at stake = volume shipped by the flagged lines in the last 12 closed months.')
sp(6)
h3('Start here: the ten codes worth a decision this cycle')
W=pd.read_csv('analysis/out/a5_watchlist_full.csv')
CLd=pd.read_csv('analysis/out/a4_cutlines.csv')
picks=[
 ('Kylie Skin Tint Foundation (00006730)','ULTA','Service',
  '731K units lost against 746K delivered — a 49.5% cut rate, sustained since January 2025. The largest single '
  'recoverable loss in the scope, and it is booked to grow.',CRIT),
 ('Gucci Face Bronzing Powder (00005685)','ALL_OTHERS','Service',
  '58.9% of demand lost. More units refused than delivered, sustained since January 2025.',CRIT),
 ('Gorgeous Gardenia (00005915)','ALL_OTHERS','Consumer decline',
  'Your largest code at 1.49M units. EPOS down 49% over six months while the forward book is set at '
  '145% of the trailing year. Both cannot be right.',CRIT),
 ('Gucci Guilty PH Eau de Parfum (00005405)','ALL_OTHERS','Over-booked + decline',
  'Booked at 2.9x the trailing twelve months while EPOS falls 36%. Also carries the single largest '
  'untraceable residual in the forward book (+1.25M units).',CRIT),
 ('Gucci Flora Gorgeous Gardenia Intense (00007022)','ALL_OTHERS','Lost forecast',
  '638K units shipped in the last year against a forward book of 76K. Either it is being delisted or '
  'supply is about to be blindsided.',CRIT),
 ('Kylie Jenner Mood Stones (00007046)','ULTA','Lost forecast + cliff',
  '415K units shipped in six months; the forecast stops dead at 2026.M08. A launch that was never '
  'extended.',CRIT),
 ('Cosmic Kylie Jenner INTENSE (00007045)','ULTA','Lost forecast + cliff',
  '299K units and rising fast (+384% sell-in, +470% EPOS — genuine consumer demand), forward book 16K.',CRIT),
 ('Gucci Guilty New27 pour Homme (00007262)','ALL_OTHERS','Over-booked',
  'Booked at 10.8x the trailing year. May be a legitimate launch ramp, but it needs a named assumption '
  'against it — 687K units is a large bet.',SERIOUS),
 ('Gucci Matt Foundation (00006173)','ALL_OTHERS','Service',
  '67% of demand lost since January 2025. Part of the Gucci Make up colour cluster that needs a '
  'category-level supply answer.',CRIT),
 ('Cosmic Kylie Jenner Pearl (00007271)','ALL_OTHERS','Phantom',
  '507K units in the forward book on a line with zero shipments in the last 12 months. If the launch '
  'is real, fine — if it slipped, supply is building to a date that moved.',SERIOUS),
]
rows=[]
for pl,cfg,flag,why,c in picks:
    rows.append([Paragraph(f'<b>{pl}</b>',ST['td']),cfg,
      Paragraph(f'<font color="#{c.hexval()[2:]}"><b>{flag}</b></font>',ST['td']),
      Paragraph(why,ST['tdm'])])
E.append(table(['Product line','Group','Flag','Why it matters'],rows,
    [CW*0.25,CW*0.15,CW*0.14,CW*0.46]))
sp(8)
E.append(Callout('How to work the list',
  'Take the service flags first — that demand is already won and needs no forecasting judgement, only a '
  'supply conversation. Then the lost-forecast and cliff codes, which are maintenance and take minutes. '
  'Leave over- and under-booked for last: they need a real conversation with the commercial team, and '
  'the answer is usually a named assumption rather than a number change.',S1,BANDBLUE))
softbreak()

# ============================== 14. APPENDICES ==============================
sec('14 · Appendices')
h2('14 · Appendices')
h3('A · Gucci Fragrance Multiline (00003484), reported separately')
ml=s7['multiline']
p(f'This line was excluded from every aggregate in the report. In the last twelve closed months it '
  f'shipped <b>{u(ml["vol12"])} units — {pct(ml["share"],0)} of the entire scope</b>. Left in, it would '
  'have dominated every average, every seasonal index and every concentration figure.')
fig('c18_multiline.png','Monthly sell-in of the excluded line. This is not a product series; it is a '
    'sequence of batches.')
bl([f'<b>It moves in blocks.</b> Its biggest month was {ml["spike"]["month"].replace(".M","-")} at '
    f'{u(ml["spike"]["units"])} units — <b>{ml["spike"]["x"]:.0f} times its own median month</b>. A '
    'seasonal index calculated on it swings from 2 in June to 304 in September.',
    f'<b>It has almost no consumer signal.</b> EPOS over the last twelve months totals '
    f'{u(ml["epos"])} units against {u(ml["vol12"])} shipped — a ratio of {ml["epos_ratio"]:.3f}. '
    'Whatever this line represents, it barely registers at the till.',
    f'<b>Service on it is excellent</b> ({u(ml["cuts"])} units cut) and its forward book is '
    f'{u(ml["fwd"])} units.'])
rule_box('What to do with it',
  'Treat it as an <b>aggregation or transfer line, not a product</b>. Forecast it separately, on its own '
  'logic, and keep it out of any statistical model or benchmark that mixes it with real products. Its '
  'volume alone means a 10% error on it outweighs a perfect forecast on your bottom 150 lines. It is '
  'also worth confirming internally what it actually contains — the EPOS ratio suggests it is not '
  'reaching consumers as this code.',WARN,colors.HexColor('#fdf6e3'))
E.append(PageBreak())
h3('B · What each measure contains, as observed in this extract')
mrows=[
 ('System FC - Final','The statistical engine output.',
  f'Overwritten with the actual in every closed month. Forward-looking, it contributes 40.8% of the '
  'consensus. Produces a zero in a large share of cells, which is itself a signal on intermittent codes.'),
 ('Initiative Forecast','Manual forecast for new codes with no history.',
  '13.5% of the forward book, concentrated in 2027-2029. Effectively the launch layer.'),
 ('Prometheus Fcst Consensus','A second initiative-type layer.',
  f'6.0% of the forward book, but loads large gross figures that Total Demand Assumption then nets '
  f'down — {s4["offset"]["n"]} line-months show this pattern. Always read the two together.'),
 ('Customer Fcst','Forecast submitted by the customer.',
  '<b>Completely empty across the whole extract.</b> No populated cells in any month or line.'),
 ('EPOS','Consumer offtake at the retailer.',
  f'2024.M07 to 2026.M07, one month behind actuals, covering 140 lines. Median coverage '
  f'{pct(s2["coverage"]["50%"])} of sell-in — a partial but directionally reliable signal.'),
 ('Reasonability Adjustment','Manual correction layer.',
  f'{pct(s4["dir_Rea"]["neg"],0)} of entries are negative, netting {u(s4["dir_Rea"]["net"])} units. '
  'A standing downward correction on the system.'),
 ('Total Demand Assumption','Market insight and event adjustments.',
  f'Balanced in direction ({pct(s4["dir_Tot"]["neg"],0)} negative), net +{u(s4["dir_Tot"]["net"])} units. '
  'Also carries the Prometheus offsets.'),
 ('Consensus - Final','The number sent to supply.',
  'Reconciles to the sum of the layers above in only two thirds of the forward book; the remaining 33% '
  'has no traceable origin in this extract.'),
 ('Actuals','What was shipped.',
  '2023.M08 to 2026.M09. Complete through 2026.M07; August still invoicing, September in flight.'),
 ('Supply Cuts','Orders that could not be served.',
  'The best available proxy for unconstrained demand. Rose from 3.1% of demand in 2023 to 11.9% in 2025.'),
]
rows=[[Paragraph(f'<b>{a}</b>',ST['td']),Paragraph(b,ST['td']),Paragraph(c,ST['tdm'])] for a,b,c in mrows]
E.append(table(['Measure','What it is','What this extract shows'],rows,
    [CW*0.20,CW*0.24,CW*0.56]))
sp(10)
h3('C · Method')
bl(['<b>Scope.</b> One O9 extract, sheet SCOPE, 3,030 rows at House / Brand / Product Line / CFG / '
    'Measure level, 97 monthly columns from 2022.M03 to 2030.M03.',
    '<b>Exclusion.</b> Gucci Fragrance Multiline (00003484) removed from every aggregate, both customer '
    'groups, and reported in Appendix A.',
    '<b>Closed history.</b> 2023.M08 to 2026.M07. All trend, seasonality, launch and service figures use '
    'this window only.',
    '<b>Seasonal index.</b> Computed per calendar year and then averaged, so a larger year does not '
    'dominate the shape. 100 = that series\' own average month. Full years only (2024 and 2025 for '
    'sell-in, 2025 for EPOS).',
    '<b>Launch definition.</b> First actual on or after 2023.M09, since 128 lines have their first actual '
    'in 2023.M08, which is the start of history rather than a launch. 103 launches qualify.',
    '<b>Demand lost.</b> Supply cuts / (actuals + supply cuts). Read as the share of ordered demand that '
    'was not served.',
    '<b>Lead-lag.</b> Correlation between sell-in at month T-k and EPOS at month T, tested for k of 0 to '
    '4, at both scope and product-line level.',
    '<b>Forecastability score.</b> Volatility (30 points), share of months with a shipment (25), '
    'year-on-year shape correlation (25), history depth (10), EPOS availability (10).',
    '<b>Not computed.</b> MAPE, BIAS and forecast value added — history is overwritten in O9, so no '
    'pre-actual forecast exists in this extract. See Section 1.'])
sp(8)
h3('D · What to extract next')
p('Four additions would materially deepen this analysis, in order of value:')
bl(['<b>Lag snapshots of Consensus - Final</b> at lag-1 and lag-3 against the actual that followed, for '
    '24 months. This unlocks MAPE, BIAS and forecast value added by layer — the whole accuracy dimension '
    'that is currently unavailable.',
    '<b>The missing consensus layer</b>, or confirmation that direct consensus overrides are being used. '
    'A third of your forward book is currently unattributable.',
    '<b>Retailer inventory or weeks of cover</b>, if available. Combined with the three-month lag it '
    'would turn the sell-in versus sell-out gap from a warning sign into a measurable position.',
    '<b>EPOS for the 62 lines that lack it</b>, and a note on which retailers report. Knowing the '
    'coverage base would let the ratios be read as levels rather than only as trends.'])
sp(12)
E.append(HR(CW,AXIS,1)); sp(8)
E.append(Paragraph('Prepared from <i>scope analysis.xlsx</i>. Closed history through 2026.M07. All figures '
   'in units. Aggregates exclude Gucci Fragrance Multiline (00003484).',ST['small']))

doc.build(E)
print('built: Scope Analysis Report.pdf')
