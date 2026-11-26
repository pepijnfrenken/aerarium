(function(){
  'use strict';

  var DATA = JSON.parse(document.getElementById('data').textContent);
  var SRC = {};
  DATA.meta.sources.forEach(function(s){ SRC[s.id] = s; });

  var NA = '<span class="na">n/a</span>';
  var YS = ['2022','2023','2024'];

  function esc(s){
    return String(s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function own(o,k){ return o != null && Object.prototype.hasOwnProperty.call(o,k); }
  function getY(by,y){ return own(by,y) ? by[y] : null; }
  function sumNums(xs){
    var v = xs.filter(function(x){ return x != null; });
    return v.length ? v.reduce(function(a,b){ return a+b; },0) : null;
  }
  var NF = new Intl.NumberFormat('en-GB');
  function pnum(v,d){
    if(v == null) return 'n/a';
    if(d == null) d = Math.abs(v-Math.round(v)) < 0.005 ? 0 : 2;
    return new Intl.NumberFormat('en-GB',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
  }
  function n(v){ return v == null ? NA : '<span class="nw">'+NF.format(v)+'</span>'; }
  function eur(v){
    if(v == null) return NA;
    var d = Math.abs(v-Math.round(v)) < 0.005 ? 0 : 2;
    return '<span class="nw">€\u00a0'+pnum(v,d)+'</span>';
  }
  function peur(v){
    if(v == null) return 'n/a';
    var d = Math.abs(v-Math.round(v)) < 0.005 ? 0 : 2;
    return '€ '+pnum(v,d);
  }
  function pct(v){ return v == null ? NA : pnum(v,1)+'%'; }
  function shortUrl(u){
    try { var x = new URL(u); return x.host + x.pathname; } catch(e){ return u; }
  }
  function srcTag(ids, prefix){
    return ids.map(function(id){
      var s = SRC[id];
      return '<span class="tag">Source</span>' + (prefix ? esc(prefix)+' ' : '') +
        '<a href="'+esc(s.url)+'" rel="noopener" title="'+esc(s.label)+'">'+esc(s.label)+'</a> ' +
        '<span class="url">'+esc(shortUrl(s.url))+'</span> · '+esc(s.licence);
    }).join('<br>');
  }
  function line(k,v){ return k + new Array(Math.max(2, 17-k.length)).join(' ') + v; }

  /* ---------- tips ---------- */
  var tip = document.getElementById('tip');
  function placeTip(x,y){
    var r = tip.getBoundingClientRect();
    var left = x + 14, top = y - r.height - 12;
    if(left + r.width > window.innerWidth - 8) left = x - r.width - 14;
    if(left < 8) left = 8;
    if(top < 8) top = y + 18;
    if(top + r.height > window.innerHeight - 8) top = window.innerHeight - r.height - 8;
    tip.style.left = left+'px';
    tip.style.top = top+'px';
  }
  function showTip(text,x,y){
    tip.textContent = text;
    tip.classList.add('on');
    tip.setAttribute('aria-hidden','false');
    placeTip(x,y);
  }
  function hideTip(){
    tip.classList.remove('on');
    tip.setAttribute('aria-hidden','true');
  }
  document.addEventListener('pointerover', function(e){
    var t = e.target.closest('[data-tip]');
    if(t) showTip(t.getAttribute('data-tip'), e.clientX, e.clientY);
  });
  document.addEventListener('pointermove', function(e){
    if(tip.classList.contains('on')) placeTip(e.clientX, e.clientY);
  });
  document.addEventListener('pointerout', function(e){
    if(e.target.closest('[data-tip]')) hideTip();
  });
  document.addEventListener('focusin', function(e){
    var t = e.target.closest('[data-tip]');
    if(!t) return;
    var r = t.getBoundingClientRect();
    showTip(t.getAttribute('data-tip'), r.left + r.width/2, r.top);
  });
  document.addEventListener('focusout', function(e){
    if(e.target.closest('[data-tip]')) hideTip();
  });

  /* ---------- masthead ---------- */
  document.getElementById('srcstrip').innerHTML = DATA.meta.sources.map(function(s){
    return '<div class="srccard">' +
      '<div class="sid">'+esc(s.id)+'</div>' +
      '<div class="slabel"><a href="'+esc(s.url)+'" rel="noopener">'+esc(s.label)+'</a></div>' +
      '<div class="slic">'+esc(s.licence)+'</div>' +
    '</div>';
  }).join('');


  /* ---------- latest year: 2025 ---------- */
  (function(){
    var L = DATA.latest;
    if(!L) return;
    // Every party in the file is shown, including one that appears with no figures at all. A party that
    // filed nil, or filed only the first workbook, is a disclosure fact; a party that appears in the source
    // with nothing must not vanish from the table. Requiring a positive sum hid five of the twelve parties
    // whose final-three-weeks figure is null.
    var rows = L.parties.slice();
    var max = Math.max.apply(null, rows.map(function(p){ return (p.gifts_to_8oct||0)+(p.gifts_final_3_weeks||0); }));
    var body = rows.map(function(p){
      // b is null when the party filed nothing in the supplementary workbook. That is not zero:
      // rendering it as EUR 0 states that the party disclosed no gifts in those three weeks, which
      // the document does not say. null renders as a dash and the total is marked partial.
      var b = p.gifts_final_3_weeks;
      var a = p.gifts_to_8oct;
      var bNum = (b == null) ? 0 : b;
      var tot = (a||0) + bNum;
      var w = max>0 ? (tot/max)*100 : 0;
      var wa = (tot>0 && a!=null) ? (a/tot)*100 : 0;
      var wb = tot>0 ? (bNum/tot)*100 : 0;
      var nothing = (a == null && b == null);
      var tipText = [p.partij+' \u2014 2025' + (nothing ? ' (no filing in either workbook)' : ''),
        line('Gifts to 8 Oct', peur(a)),
        line('Final 3 weeks', peur(b)),
        line('2025 to the election', peur(tot)),
        line('Debts, 22 months', peur(p.debts_22mo)),
        line('Debts, 3 weeks', peur(p.debts_3wk))].join('\n');
      return '<tr>'+
        '<td class="party">'+esc(p.partij)+
          ((p.filers && p.filers.length>1) ? ' <span class="muted">('+esc(p.filers.join(' + '))+' filed)</span>' : '')+
        '</td>'+
        '<td class="n">'+eur(a)+'</td>'+
        '<td class="n">'+eur(b)+'</td>'+
        '<td class="n total">'+eur(tot)+
          (b == null ? ' <span class="muted" title="The party filed nothing in the supplementary workbook, so this covers 1 January to 8 October only">partial</span>' : '')+'</td>'+
        '<td class="barcell"><div class="bigbar" tabindex="0" data-tip="'+esc(tipText)+'">'+
          '<span class="bfill" style="width:'+w.toFixed(2)+'%">'+
            (a ? '<i class="g" style="width:'+wa.toFixed(1)+'%"></i>' : '')+
            (b ? '<i class="g" style="width:'+wb.toFixed(1)+'%;opacity:.45"></i>' : '')+
          '</span></div></td>'+
        '<td class="n">'+eur(p.debts_22mo)+'</td>'+
        '<td class="n">'+eur(p.debts_3wk)+'</td>'+
        '<td class="n">'+(p.donors==null?NA:n(p.donors))+'</td>'+
      '</tr>';
    }).join('');
    document.getElementById('latest-table').innerHTML =
      '<table><thead><tr><th>Party</th>'+
      '<th class="n">Gifts to 8 Oct<span class="unit">2025</span></th>'+
      '<th class="n">Final 3 weeks<span class="unit">9\u201329 Oct</span></th>'+
      '<th class="n">2025 to the election<span class="unit">sum</span></th>'+
      '<th>Gifts, split<span class="unit">solid = to 8 Oct, pale = last 3 weeks</span></th>'+
      '<th class="n">Debts<span class="unit">2024\u20138 Oct 25</span></th>'+
      '<th class="n">Debts<span class="unit">9\u201329 Oct 25</span></th>'+
      '<th class="n" title="Count of donor-total rows with a positive 2025 amount, not distinct people and not a party count">Donor rows<span class="unit">2025, positive</span></th>'+
      '</tr></thead><tbody>'+body+'</tbody></table>';
    var sv = (L.seat_view || []).filter(function(x){ return x.gifts > 0 || x.seats > 0; });
    var md = (L.media || []);
    if(md.length){
      var mt = L.media_totals || {};
      document.getElementById('media-table').innerHTML =
        '<table><thead><tr><th>Party</th><th class="n">Owed to media at filing<span class="unit">balance, not spend</span></th>'+
        '<th class="n">Share of its debt</th><th class="n">Creditors</th><th>Largest single creditor</th></tr></thead><tbody>'+
        md.map(function(x){
          var top = x.creditors && x.creditors.length ? x.creditors[0] : null;
          return '<tr><td class="party">'+esc(x.partij)+
            ((x.filers && x.filers.length>1) ? ' <span class="muted">('+esc(x.filers.join(' + '))+' filed)</span>' : '')+
            '</td>'+
            '<td class="n">'+eur(x.media_eur)+'</td>'+
            '<td class="n">'+pct(x.media_share_of_debt)+'</td>'+
            '<td class="n">'+n(x.creditors ? x.creditors.length : null)+'</td>'+
            '<td class="muted">'+(top ? esc(top.crediteur)+' · '+peur(top.bedrag) : '')+'</td></tr>';
        }).join('')+'</tbody>'+
        '<tfoot><tr><td><b>Total</b></td><td class="n"><b>'+eur(mt.media_eur)+'</b></td>'+
        '<td colspan="3" class="muted">'+pnum(mt.media_share_of_debt,1)+'% of all disclosed party debt ('+peur(mt.all_debt_eur)+')</td></tr></tfoot></table>';
      document.getElementById('media-count').textContent = md.length+' parties with media debt';
      var un = L.media_unclassified || {};
      var unNames = Object.keys(un);
      var unTotal = unNames.reduce(function(a,k){ return a + un[k]; }, 0);
      document.getElementById('media-unclass').innerHTML = unNames.length
        ? '<span class="nw">'+peur(unTotal)+'</span> across '+unNames.length+' creditor names did not match any bucket and is listed as unclassified in the data rather than forced into one.'
        : 'every creditor matched a bucket.';
    }

    var cr = (L.creditors || []);
    if(cr.length){
      document.getElementById('cred-table').innerHTML =
        '<table><thead><tr><th>Party</th><th>Creditor</th><th class="n">Owed</th><th>Period covered</th><th>Neveninstelling</th></tr></thead><tbody>'+
        cr.map(function(c){
          return '<tr><td class="party">'+esc(c.partij)+'</td><td>'+esc(c.crediteur)+'</td>'+
            '<td class="n">'+eur(c.bedrag)+'</td><td class="muted">'+esc(c.period)+'</td>'+
            '<td class="muted">'+(c.neveninstelling || '')+'</td></tr>';
        }).join('')+'</tbody></table>';
      document.getElementById('cred-count').textContent =
        cr.length+' of '+L.creditor_count+' creditor rows · largest first';
    }

    document.getElementById('latest-seat').innerHTML =
      '<table><thead><tr><th>List</th><th class="n">Seats<span class="unit">2025</span></th>'+
      '<th class="n">Gifts, 2025 to election</th><th class="n">Gifts per seat</th><th>Filed as</th></tr></thead><tbody>'+
      sv.map(function(x){
        return '<tr>'+
          '<td class="party">'+esc(x.lijst)+'</td>'+
          '<td class="n">'+n(x.seats)+'</td>'+
          '<td class="n">'+eur(x.gifts)+'</td>'+
          '<td class="n total">'+(x.per_seat==null ? '<span class="na">no seat</span>' : eur(x.per_seat))+'</td>'+
          '<td class="muted">'+esc(x.filers.join(' + '))+'</td>'+
        '</tr>';
      }).join('')+'</tbody></table>';
    document.getElementById('seat-count').textContent =
      sv.filter(function(x){ return x.seats>0; }).length+' lists with seats';

    document.getElementById('latest-count').textContent = rows.length+' parties with 2025 gifts';
    document.getElementById('latest-lede').innerHTML =
      'The dashboard stops at 2024. <b>2025 is published somewhere else:</b> BZK released ODS overviews for the '+
      'Tweede Kamer election of 29 October 2025, covering gifts from 1 January 2024 to 8 October 2025, plus a '+
      'supplementary set for the final three weeks. <b>\u20ac\u00a0'+pnum(L.total_to_election,2)+'</b> in gifts '+
      'reached parties in 2025 up to election day, against \u20ac\u00a0'+pnum(L.total_2024_full_year,2)+' in all of 2024.';
    document.getElementById('latest-note').textContent = L.note;
    document.getElementById('latest-src').innerHTML = srcTag(['tk2025','tk2025post']);
  })();

  /* ---------- money map ---------- */
  var pmap = {};
  function party(name){
    if(!pmap[name]) pmap[name] = {name:name, sub:null, gift:null};
    return pmap[name];
  }
  DATA.subsidy.parties.forEach(function(p){ party(p.name).sub = p.by_year; });
  DATA.gifts.parties.forEach(function(p){ party(p.name).gift = p.by_year; });

  var parties = Object.keys(pmap).map(function(k){
    var p = pmap[k];
    var subSum = sumNums(YS.map(function(y){ return getY(p.sub,y); }));
    var giftSum = sumNums(YS.map(function(y){ return getY(p.gift,y); }));
    var total = (subSum || 0) + (giftSum || 0);
    var share = (giftSum != null && total > 0) ? (giftSum / total) * 100 : null;
    return {name:p.name, sub:p.sub, gift:p.gift, subSum:subSum, giftSum:giftSum, total:total, share:share};
  }).sort(function(a,b){ return b.total - a.total; });

  var maxTotal = Math.max.apply(null, parties.map(function(p){ return p.total; }));
  var mapRows = parties.map(function(p){
    var w = maxTotal > 0 ? (p.total / maxTotal) * 100 : 0;
    var subW = p.total > 0 && p.subSum != null ? (p.subSum / p.total) * 100 : 0;
    var giftW = p.total > 0 && p.giftSum != null ? (p.giftSum / p.total) * 100 : 0;
    var tipText = [
      p.name + ' — 2022–2024',
      line('State subsidy', peur(p.subSum)),
      line('Private gifts', peur(p.giftSum)),
      line('Two-source subtotal', peur(p.total)),
      line('Gift share', p.share == null ? 'n/a' : pnum(p.share,1)+' % (computed)')
    ].join('\n');

    var mins = YS.map(function(y){
      var s = getY(p.sub,y), g = getY(p.gift,y);
      var t = (s || 0) + (g || 0);
      var scale = 0;
      YS.forEach(function(yy){
        var ss = getY(p.sub,yy), gg = getY(p.gift,yy);
        if(ss != null || gg != null) scale = Math.max(scale, (ss||0)+(gg||0));
      });
      var fw = scale > 0 ? (t / scale) * 100 : 0;
      var sw = t > 0 && s != null ? (s / t) * 100 : 0;
      var gw = t > 0 && g != null ? (g / t) * 100 : 0;
      var mTip = [
        p.name + ' — ' + y,
        line('State subsidy', peur(s)),
        line('Private gifts', peur(g)),
        line('Total', peur((s == null && g == null) ? null : t))
      ].join('\n');
      if(s == null && g == null){
        return '<td class="minicell"><span class="na" aria-label="'+esc(p.name+' '+y+': n/a')+'">n/a</span></td>';
      }
      var inner = '<span class="mf" style="width:'+fw.toFixed(1)+'%">' +
            (s != null ? '<i class="s" style="width:'+sw.toFixed(1)+'%"></i>' : '') +
            (g != null ? '<i class="g" style="width:'+gw.toFixed(1)+'%"></i>' : '') +
          '</span>';
      return '<td class="minicell">' +
        '<div class="mini" tabindex="0" data-tip="'+esc(mTip)+'"' +
        ' aria-label="'+esc(p.name+' '+y+': subsidy '+peur(s)+', gifts '+peur(g))+'">'+inner+'</div>' +
      '</td>';
    }).join('');

    return '<tr>' +
      '<td class="party">'+esc(p.name)+'</td>' +
      '<td class="n">'+eur(p.subSum)+'</td>' +
      '<td class="n">'+eur(p.giftSum)+'</td>' +
      '<td class="share'+(p.share != null && p.share >= 50 ? ' dom' : '')+'">'+pct(p.share)+'</td>' +
      '<td class="barcell"><div class="bigbar" tabindex="0" data-tip="'+esc(tipText)+'" aria-label="'+esc(p.name+' total '+peur(p.total))+'">' +
        '<span class="bfill" style="width:'+w.toFixed(2)+'%">' +
          (p.subSum ? '<i class="s" style="width:'+subW.toFixed(1)+'%"></i>' : '') +
          (p.giftSum ? '<i class="g" style="width:'+giftW.toFixed(1)+'%"></i>' : '') +
        '</span>' +
      '</div></td>' +
      mins +
      '<td class="n total">'+eur(p.total)+'</td>' +
    '</tr>';
  }).join('');

  document.getElementById('map-table').innerHTML =
    '<table><thead><tr>' +
      '<th>Party</th>' +
      '<th class="n">State subsidy<span class="unit">2022–24</span></th>' +
      '<th class="n">Private gifts<span class="unit">2022–24</span></th>' +
      '<th class="n" title="Gift totals include transfers from a party\'s own foundations and salary transfers from its own representatives; they are gross of internal movement and do not measure outside influence.">Gift share, gross<span class="unit">computed</span></th>' +
      '<th>Income, stacked</th>' +
      '<th class="n">2022</th><th class="n">2023</th><th class="n">2024</th>' +
      '<th class="n">Total<span class="unit">2022–24</span></th>' +
    '</tr></thead><tbody>'+mapRows+'</tbody></table>';

  document.getElementById('map-count').textContent = parties.length+' parties';
  document.getElementById('map-lede').innerHTML =
    'Income over 2022–2024 for every party that appears in either source. ' +
    'Gift share is <b>private gifts ÷ (private gifts + state subsidy)</b>, computed from the embedded JSON; ' +
    'missing years are excluded, never replaced by zero. ' +
    '<b>GroenLinks and PvdA are one party now:</b> they filed separately every year here, but campaigned on one ' +
    'list from 2023 and became PRO on 1 July 2026, so read those two rows together. Combined they are ' +
    '€ 20.529.188 over the window, more than VVD.';
  document.getElementById('map-src').innerHTML = srcTag(['subsidy','gifts']);

  /* ---------- cross party ---------- */
  var cross = DATA.gifts.cross_party.slice().sort(function(a,b){ return b.total - a.total; });
  var crossSum = cross.reduce(function(a,c){ return a + c.total; }, 0);
  document.getElementById('cross-lede').innerHTML =
    '<b>'+cross.length+' donor-year cases</b> in which the same donor gave to more than one <b>filing party</b> in the same year; ' +
    'GroenLinks and PvdA filed separately throughout this period and are counted as two filers here, not as PRO. ' +
    'Together these cases account for <b>'+eur(crossSum)+'</b>. Each case appears once, with the amount per party.';

  var crossRows = cross.map(function(c){
    var bp = Object.keys(c.by_party).map(function(k){ return [k, c.by_party[k]]; })
      .sort(function(a,b){ return b[1]-a[1]; });
    var chips = bp.map(function(x){
      return '<span class="pp"><span class="pn">'+esc(x[0])+'</span><span class="pv">'+eur(x[1])+'</span></span>';
    }).join('');
    var xb = bp.map(function(x){
      return '<i style="width:'+((x[1]/c.total)*100).toFixed(1)+'%"></i>';
    }).join('');
    var xbTip = [c.donor+' — '+c.jaar]
      .concat(bp.map(function(x){ return line(x[0], peur(x[1])); }))
      .join('\n');
    return '<tr>' +
      '<td>'+esc(c.donor)+'</td>' +
      '<td class="n">'+esc(c.jaar)+'</td>' +
      '<td>'+esc(c.parties.join(' · '))+'</td>' +
      '<td>'+chips+'<div class="xbar" data-tip="'+esc(xbTip)+'" aria-hidden="true">'+xb+'</div></td>' +
      '<td class="n total">'+eur(c.total)+'</td>' +
    '</tr>';
  }).join('');

  document.getElementById('cross-table').innerHTML =
    '<table><thead><tr>' +
      '<th>Donor (as published)</th><th class="n">Year</th><th>Parties</th>' +
      '<th>Amount per party</th><th class="n">Total</th>' +
    '</tr></thead><tbody>'+crossRows+'</tbody></table>';
  document.getElementById('cross-src').innerHTML = srcTag(['gifts']);

  /* ---------- donor typology ---------- */
  var TYPO = DATA.typology;
  var TORDER = ['individual', 'entity', 'bequest', 'party_vehicle'];
  var TNAME = {individual:'individuals', entity:'entities', bequest:'bequests', party_vehicle:'party vehicles'};
  var TSHORT = {individual:'individual', entity:'entity', bequest:'bequest', party_vehicle:'vehicle'};
  var TSEG = {individual:'ti', entity:'te', bequest:'tb', party_vehicle:'tv'};
  var TSW = {individual:'', entity:' ent', bequest:' beq', party_vehicle:' veh'};
  var tCounts = TYPO.counts, tMoney = TYPO.money;
  var typDonors = TORDER.reduce(function(a,k){ return a + (tCounts[k] || 0); }, 0);
  var typTotal = TORDER.reduce(function(a,k){ return a + (tMoney[k] || 0); }, 0);

  var typParts = TORDER.map(function(k){
    return '<b>'+NF.format(tCounts[k] || 0)+'</b> '+TNAME[k]+' ('+eur(tMoney[k] || 0)+')';
  });
  var typLast = typParts.pop();
  document.getElementById('typ-lede').innerHTML =
    '<b>'+NF.format(typDonors)+' donors</b> gave <b>'+eur(typTotal)+'</b> in 2022–2024, ' +
    'split into four classes by name and by the register’s own entity tags: ' +
    typParts.join(', ')+' and '+typLast+'.';

  document.getElementById('typ-legend').innerHTML =
    TORDER.map(function(k){
      return '<span class="key"><i class="sw'+TSW[k]+'"></i>'+TNAME[k]+'</span>';
    }).join('') +
    '<span>One bar per party, sorted by total gifts. Bar length is the party total on a shared scale; each segment is that party’s split by donor class.</span>';

  var typParties = Object.keys(TYPO.by_party).map(function(k){
    var p = TYPO.by_party[k];
    return {name:k, total:p.total, eshare:p.entity_share,
      vals:TORDER.map(function(c){ return p[c] || 0; })};
  }).sort(function(a,b){ return b.total - a.total; });
  var typMax = typParties.length ? typParties[0].total : 0;

  document.getElementById('typ-bars').innerHTML = typParties.map(function(p){
    var fillW = typMax > 0 ? (p.total / typMax) * 100 : 0;
    var segs = p.vals.map(function(amt,i){
      if(!amt || p.total <= 0) return '';
      var c = TORDER[i];
      var w = (amt / p.total) * 100;
      var segTip = [
        p.name + ' — ' + TSHORT[c],
        line('Amount', peur(amt)),
        line('Party share', pnum(w,1)+' %')
      ].join('\n');
      return '<i class="'+TSEG[c]+'" style="width:'+w.toFixed(2)+'%" tabindex="0"' +
        ' data-tip="'+esc(segTip)+'"' +
        ' aria-label="'+esc(p.name+' '+TSHORT[c]+': '+peur(amt)+', '+pnum(w,1)+'% of the party total')+'"></i>';
    }).join('');
    return '<div class="typrow">' +
      '<span class="typparty">'+esc(p.name)+'</span>' +
      '<div class="typtrack"><span class="typfill" style="width:'+fillW.toFixed(2)+'%">'+segs+'</span></div>' +
      '<span class="typtot">'+eur(p.total)+'</span>' +
    '</div>';
  }).join('');

  document.getElementById('typ-table').innerHTML =
    '<table><thead><tr>' +
      '<th>Party</th>' +
      '<th class="n">Total<span class="unit">€ · 2022–24</span></th>' +
      '<th class="n">Individual<span class="unit">€</span></th>' +
      '<th class="n">Entity<span class="unit">€</span></th>' +
      '<th class="n">Bequest<span class="unit">€</span></th>' +
      '<th class="n">Vehicle<span class="unit">€</span></th>' +
      '<th class="n">Entity share<span class="unit">computed</span></th>' +
    '</tr></thead><tbody>' +
    typParties.map(function(p){
      var cells = p.vals.map(function(amt){
        return '<td class="n">'+(amt ? eur(amt) : '<span class="muted">'+eur(0)+'</span>')+'</td>';
      }).join('');
      return '<tr>' +
        '<td class="party">'+esc(p.name)+'</td>' +
        '<td class="n total">'+eur(p.total)+'</td>' +
        cells +
        '<td class="share">'+pnum(p.eshare,1)+'%</td>' +
      '</tr>';
    }).join('') +
    '</tbody><tfoot><tr>' +
      '<td class="party">All parties</td>' +
      '<td class="n total">'+eur(typTotal)+'</td>' +
      TORDER.map(function(k){ return '<td class="n">'+eur(tMoney[k] || 0)+'</td>'; }).join('') +
      '<td></td>' +
    '</tr></tfoot></table>';

  document.getElementById('typ-count').textContent =
    'typology.by_party · '+typParties.length+' parties';
  document.getElementById('typ-note').innerHTML =
    '<b>On the classes.</b> '+esc(TYPO.warning)+' ' +
    'An entity share measures the kind of donor, not the donor’s influence: for SP, GL and PvdA most of the ' +
    '“individual” money is their own elected representatives transferring their allowance to the party under a party rule.';
  document.getElementById('typ-src').innerHTML = srcTag(['gifts']);

  /* ---------- gift entities ---------- */
  var emap = {}, emapKeys = [];
  DATA.gifts.donors.forEach(function(d){
    d.edges.forEach(function(e){
      if(!e.entity) return;
      if(!emap[e.entity]){ emap[e.entity] = {name:e.entity, total:0, n:0, parties:{}, years:{}}; emapKeys.push(e.entity); }
      var x = emap[e.entity];
      x.total += (e.bedrag || 0);
      x.n += 1;
      x.parties[e.partij] = true;
      x.years[e.jaar] = true;
    });
  });
  var ents = emapKeys.map(function(k){ return emap[k]; })
    .sort(function(a,b){ return b.total - a.total; });
  var maxEnt = ents.length ? Math.max.apply(null, ents.map(function(e){ return e.total; })) : 0;

  document.getElementById('ent-count').textContent = ents.length+' distinct entity names';
  document.getElementById('ent-table').innerHTML =
    '<table><thead><tr>' +
      '<th>Entity (as published)</th><th>Party on the edge</th><th>Relative total</th>' +
      '<th class="n">Gifts received</th><th class="n">Gift edges</th>' +
    '</tr></thead><tbody>' +
    ents.map(function(e){
      var partyList = Object.keys(e.parties).join(' / ');
      var eTip = [
        e.name,
        line('Party on edge', partyList),
        line('Gifts received', peur(e.total)),
        line('Gift edges', String(e.n))
      ].join('\n');
      return '<tr>' +
        '<td>'+esc(e.name)+'</td>' +
        '<td>'+esc(partyList)+'</td>' +
        '<td><div class="bigbar" style="height:9px" tabindex="0" data-tip="'+esc(eTip)+'" aria-label="'+esc(e.name+': '+peur(e.total))+'"><i class="g" style="width:'+((e.total/maxEnt)*100).toFixed(1)+'%"></i></div></td>' +
        '<td class="n">'+eur(e.total)+'</td>' +
        '<td class="n">'+n(e.n)+'</td>' +
      '</tr>';
    }).join('') +
    '</tbody></table>';
  document.getElementById('ent-src').innerHTML = srcTag(['gifts'], 'Entity totals derived from gifts.donors[].edges;');

  /* ---------- NFRP ---------- */
  var nmap = {}, nkeys = [];
  DATA.nfrp.forEach(function(r){
    if(!nmap[r.entity]){ nmap[r.entity] = {name:r.entity, kvk:r.kvk, years:{}, total:0}; nkeys.push(r.entity); }
    var x = nmap[r.entity];
    if(!x.kvk && r.kvk) x.kvk = r.kvk;
    x.years[r.jaar] = (x.years[r.jaar] || 0) + r.bedrag_k;
    x.total += r.bedrag_k;
  });
  var nfrpEntities = nkeys.map(function(k){ return nmap[k]; })
    .sort(function(a,b){ return b.total - a.total; });
  var nfrpYears = Array.from(new Set(DATA.nfrp.map(function(r){ return r.jaar; }))).sort(function(a,b){ return a-b; });
  var nfrpYearTotals = {};
  nfrpYears.forEach(function(y){
    nfrpYearTotals[y] = DATA.nfrp.filter(function(r){ return r.jaar === y; })
      .reduce(function(a,r){ return a + r.bedrag_k; }, 0);
  });
  var nfrpGrand = DATA.nfrp.reduce(function(a,r){ return a + r.bedrag_k; }, 0);

  var anon = (DATA.nfrp_anon || []);
  if(anon.length){
    var anonTotal = anon.reduce(function(a,r){ return a + r.bedrag_k; }, 0);
    var bits = anon.map(function(r){ return r.jaar+': '+pnum(r.bedrag_k); });
    document.getElementById('nfrp-anon').innerHTML =
      '<b>Part of this is anonymised and is not in the table below.</b> Anonymised NFRP rows total '+
      '<span class="nw">\u20ac\u00a0'+pnum(anonTotal,0)+'k</span> ('+esc(bits.join(', '))+'), so the named rows '+
      'are a share of the scheme, not all of it.';
  }
  // 24 records in DATA.nfrp are entity-YEAR aggregates, not source rows. An audit found the badge
  // reporting them as "register rows", which understated the source by half and hid the spelling
  // variants the join had to absorb.
  (function(){
    var srcRows = DATA.nfrp.reduce(function(a,r){ return a + (r.rows || 0); }, 0);
    var spell = {};
    DATA.nfrp.forEach(function(r){ (r.variants || []).forEach(function(v){ spell[v] = 1; }); });
    document.getElementById('nfrp-count').textContent =
      nfrpEntities.length + ' entities · ' + Object.keys(spell).length + ' spellings · ' +
      srcRows + ' source rows in ' + DATA.nfrp.length + ' entity-years';
  })();
  document.getElementById('nfrp-table').innerHTML =
    '<table><thead><tr>' +
      '<th>Entity (as published)</th><th>KVK</th>' +
      nfrpYears.map(function(y){ return '<th class="n">'+y+'<span class="unit">€k</span></th>'; }).join('') +
      '<th class="n">Total<span class="unit">€k</span></th>' +
    '</tr></thead><tbody>' +
    nfrpEntities.map(function(e){
      return '<tr>' +
        '<td>'+esc(e.name)+'</td>' +
        '<td class="n">'+(e.kvk == null ? NA : esc(e.kvk))+'</td>' +
        nfrpYears.map(function(y){ return '<td class="n">'+(own(e.years,y) ? n(e.years[y]) : NA)+'</td>'; }).join('') +
        '<td class="n total">'+n(e.total)+'</td>' +
      '</tr>';
    }).join('') +
    '</tbody><tfoot><tr>' +
      '<td class="party">All entities</td><td></td>' +
      nfrpYears.map(function(y){ return '<td class="n">'+n(nfrpYearTotals[y])+'</td>'; }).join('') +
      '<td class="n total">'+n(nfrpGrand)+'</td>' +
    '</tr></tfoot></table>';
  document.getElementById('nfrp-src').innerHTML = srcTag(['nfrp']);

  /* ---------- what the entities do ---------- */
  (function(){
    var F = DATA.neven_functie || [];
    if(!F.length) return;
    function rows(){
      return F.map(function(e){
        return '<tr>'+
          '<td class="party">'+esc(e.entiteit)+'</td>'+
          '<td class="muted">'+esc(e.partij)+'</td>'+
          '<td>'+esc(e.functie)+'</td>'+
          '<td class="muted">'+esc(e.soort||'')+'</td>'+
          '<td>'+(e.certainty==='sourced' && e.bron_url
                 ? '<a href="'+esc(e.bron_url)+'" rel="noopener">source</a>'
                 : '<span class="na">from the name</span>')+'</td>'+
        '</tr>';
      }).join('');
    }
    document.getElementById('functie-table').innerHTML =
      '<table><thead><tr><th>Entity</th><th>Filed by</th><th>What it does</th><th>Type</th><th>Basis</th></tr></thead>'+
      '<tbody>'+rows()+'</tbody></table>';
    document.getElementById('fn-count').textContent =
      F.filter(function(e){ return e.certainty==='sourced'; }).length+' of '+F.length+' sourced';
  })();

  /* ---------- budget ---------- */
  var bud = DATA.budget.slice().sort(function(a,b){ return a.jaar - b.jaar; });
  var maxB = Math.max.apply(null, bud.reduce(function(a,r){
    a.push(r.ceiling_k);
    if(r.realised_k != null) a.push(r.realised_k);
    return a;
  }, []));
  var step = 10000;
  var gridVals = [];
  for(var g = 0; g <= maxB; g += step) gridVals.push(g);

  var cols = bud.map(function(r){
    var plotH = 190;
    var realH = r.realised_k == null ? 0 : (r.realised_k / maxB) * 100;
    var namedH = (r.realised_k && r.named_k != null)
      ? Math.min(100, (r.named_k / r.realised_k) * 100) : 0;
    var ceilB = (r.ceiling_k / maxB) * 100;
    var mark = r.jaar === 2024 ? ' mark' : '';
    var tipText = [
      r.jaar + ' — all amounts in € thousand',
      line('Ceiling', r.ceiling_k == null ? 'n/a' : pnum(r.ceiling_k)),
      line('Realised', r.realised_k == null ? 'n/a' : pnum(r.realised_k)),
      line('Named part', r.named_k == null ? 'n/a' : pnum(r.named_k)),
      line('Anonymous part', r.anon_k == null ? 'n/a' : pnum(r.anon_k)),
      line('Disclosure', r.r4)
    ].join('\n');
    return '<div class="bcol'+mark+'">' +
      '<div class="ceil" style="bottom:'+ceilB.toFixed(2)+'%"></div>' +
      (r.realised_k == null
        ? '<div class="rbar none" tabindex="0" data-tip="'+esc(tipText)+'"></div>'
        : '<div class="rbar" style="height:'+realH.toFixed(2)+'%" tabindex="0" data-tip="'+esc(tipText)+'" aria-label="'+esc(r.jaar+' ceiling '+pnum(r.ceiling_k)+' realised '+pnum(r.realised_k))+'">' +
            '<div class="named" style="height:'+namedH.toFixed(2)+'%"></div>' +
          '</div>') +
      '<div class="ylab">'+r.jaar+'</div>' +
    '</div>';
  }).join('');

  document.getElementById('budget-chart').innerHTML =
    '<div class="chartgrid">' +
      '<div class="yaxis">'+gridVals.map(function(v){
        return '<span style="bottom:'+((v/maxB)*100).toFixed(2)+'%">'+(v===0?'0':NF.format(v))+'</span>';
      }).join('')+'</div>' +
      '<div class="plotarea">' + gridVals.map(function(v){
        return '<div class="gl'+ (v===0?' zero':'') +'" style="bottom:'+((v/maxB)*100).toFixed(2)+'%"></div>';
      }).join('') +
      '<div class="cols">'+cols+'</div></div>' +
    '</div>';

  document.getElementById('budget-table').innerHTML =
    '<table><thead><tr>' +
      '<th>Year</th><th class="n">Ceiling<span class="unit">€k</span></th><th class="n">Realised<span class="unit">€k</span></th>' +
      '<th class="n">Named<span class="unit">€k</span></th><th class="n">Anonymous<span class="unit">€k</span></th>' +
      '<th class="n">Δ realised − ceiling<span class="unit">€k</span></th><th>r4 status</th>' +
    '</tr></thead><tbody>' +
    bud.map(function(r){
      var delta = r.realised_k == null ? null : r.realised_k - r.ceiling_k;
      return '<tr'+(r.jaar === 2024 ? ' class="hot"' : '')+'>' +
        '<td class="party">'+r.jaar+'</td>' +
        '<td class="n">'+n(r.ceiling_k)+'</td>' +
        '<td class="n">'+n(r.realised_k)+'</td>' +
        '<td class="n">'+n(r.named_k)+'</td>' +
        '<td class="n">'+n(r.anon_k)+'</td>' +
        '<td class="delta'+(delta != null && delta > 0 ? ' pos' : '')+'">'+(delta == null ? NA : (delta > 0 ? '+' : '')+n(delta))+'</td>' +
        '<td class="r4">'+esc(r.r4)+'</td>' +
      '</tr>';
    }).join('') +
    '</tbody></table>';
  document.getElementById('budget-src').innerHTML = srcTag(['budget']);

  /* ---------- notes ---------- */
  document.getElementById('rules').innerHTML = DATA.meta.rules.map(function(r){
    return '<li>'+esc(r)+'</li>';
  }).join('');

  var caveats = [
    'The ANNUAL dashboard series covers gifts for 2022–2024 only. 2025 is published elsewhere and is shown in section 02 above, from the separate BZK election workbooks. 2026 does not exist yet: annual reports are due 1 July 2027.',
    'Donor names are published as written and are not merged, so variants of one name appear separately.',
    'The state subsidy to a party’s neveninstellingen is not split out in any structured source.',
    'A null value is rendered “n/a” and is never substituted with 0. A true 0 in the source is shown as € 0.',
    'Gift share is computed from the embedded JSON as gifts ÷ (gifts + subsidy) over 2022–2024; it is labelled as a share, not a published figure.'
  ];
  document.getElementById('caveats').innerHTML = caveats.map(function(c){
    return '<li>'+esc(c)+'</li>';
  }).join('');

  document.getElementById('fine').textContent =
    'Readings: subsidy and gift amounts are euros; budget and NFRP amounts are € thousand. ' +
    'Party totals exclude years a source does not publish for that party. ' +
    'The gift-entity table counts gift edges, not unique donors; no entity name is merged with another.';

  document.getElementById('foot-meta').textContent =
    'dataset generated '+DATA.meta.generated_at+' · '+DATA.meta.sources.length+' sources · '+DATA.gifts.donors.length+' donors · no network requests';
})();
