(function () {
  'use strict';

  var DATA = window.SCHEDULE_DATA;
  if (!DATA) {
    document.getElementById('schedule').innerHTML =
      '<div class="empty" style="padding:40px;"><div class="empty-icon">⚠️</div><div>课表数据未加载</div></div>';
    return;
  }

  // ========== 全局状态 ==========
  var state = {
    college: null,
    major: null,
    className: null,
    week: 0
  };

  var DAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
  var PERIOD_LABELS = ['第1-2节', '第3-4节', '第5-6节', '第7-8节', '第9-10节'];
  var TOTAL_WEEKS = DATA.totalWeeks || 19;
  var START_DATE = parseDateISO(DATA.startDate || '2025-09-08');

  document.getElementById('semesterMeta').textContent =
    (DATA.semester || '2025-2026学年 第1学期') + ' · 共 ' + TOTAL_WEEKS + ' 周';

  // ========== 工具函数 ==========
  function parseDateISO(s) {
    var parts = s.split('-');
    return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
  }
  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function getCurrentWeek() {
    if (!START_DATE) return -1;
    var now = new Date();
    var diff = Math.floor((now - START_DATE) / (1000 * 60 * 60 * 24));
    var w = Math.floor(diff / 7) + 1;
    if (w < 1 || w > TOTAL_WEEKS) return -1;
    return w;
  }
  function hashStr(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) {
      h = (h * 31 + s.charCodeAt(i)) >>> 0;
    }
    return h;
  }
  function escapeHtml(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function formatWeeks(weeks) {
    if (!weeks || weeks.length === 0) return '';
    if (weeks.length <= 8) return weeks.join(',') + ' 周';
    var sorted = weeks.slice().sort(function (a, b) { return a - b; });
    var ranges = [];
    var s = sorted[0], p = sorted[0];
    for (var i = 1; i < sorted.length; i++) {
      if (sorted[i] === p + 1) { p = sorted[i]; }
      else { ranges.push(s === p ? String(s) : s + '-' + p); s = sorted[i]; p = sorted[i]; }
    }
    ranges.push(s === p ? String(s) : s + '-' + p);
    return ranges.join(',') + ' 周';
  }

  // ========== 渲染选择项 ==========
  function renderList(container, items, onSelect) {
    container.innerHTML = '';
    if (!items || items.length === 0) {
      container.innerHTML =
        '<div class="empty" style="padding:20px;"><div class="empty-icon">🔍</div><div>暂无匹配项</div></div>';
      return;
    }
    var frag = document.createDocumentFragment();
    for (var i = 0; i < items.length; i++) {
      (function (it) {
        var div = document.createElement('div');
        div.className = 'select-item';
        div.innerHTML = '<div>' + escapeHtml(it.label) + '</div>' +
          (it.badge ? '<span class="badge">' + escapeHtml(it.badge) + '</span>' : '');
        div.addEventListener('click', function () {
          try { onSelect(it); } catch (e) { console.error(e); }
        });
        frag.appendChild(div);
      })(items[i]);
    }
    container.appendChild(frag);
  }

  function bindSearch(inputId, buildItems, container, onSelect) {
    var input = document.getElementById(inputId);
    function refresh() {
      var kw = input ? input.value.trim() : '';
      var all = buildItems();
      var filtered = !kw ? all : all.filter(function (it) {
        var hay = (it.label + ' ' + (it.keywords || '')).toLowerCase();
        return hay.indexOf(kw.toLowerCase()) >= 0;
      });
      renderList(container, filtered, onSelect);
    }
    if (input) { input.addEventListener('input', refresh); input.value = ''; }
    refresh();
  }

  // ========== 数据查找 ==========
  function findCollege() {
    for (var i = 0; i < DATA.colleges.length; i++) {
      if (DATA.colleges[i].college === state.college) return DATA.colleges[i];
    }
    return null;
  }
  function findMajor(college) {
    college = college || findCollege();
    if (!college) return null;
    for (var i = 0; i < college.majors.length; i++) {
      if (college.majors[i].major === state.major) return college.majors[i];
    }
    return null;
  }
  function findClass(major) {
    major = major || findMajor();
    if (!major) return null;
    for (var i = 0; i < major.classes.length; i++) {
      if (major.classes[i].className === state.className) return major.classes[i];
    }
    return null;
  }

  // ========== 步骤切换 ==========
  var stepIds = ['stepCollege', 'stepMajor', 'stepClass', 'scheduleCard'];
  function showStep(id) {
    for (var i = 0; i < stepIds.length; i++) {
      var el = document.getElementById(stepIds[i]);
      if (el) el.style.display = (stepIds[i] === id) ? '' : 'none';
    }
  }

  function stepCollege() {
    showStep('stepCollege');
    bindSearch('collegeSearch', function () {
      return DATA.colleges.map(function (c) {
        var cnt = 0;
        for (var i = 0; i < c.majors.length; i++) cnt += c.majors[i].classes.length;
        return { label: c.display, keywords: c.college, value: c.college, badge: cnt + ' 个班级' };
      });
    }, document.getElementById('collegeGrid'), function (it) {
      state.college = it.value;
      stepMajor();
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function stepMajor() {
    showStep('stepMajor');
    var college = findCollege();
    if (!college) { stepCollege(); return; }
    bindSearch('majorSearch', function () {
      return college.majors.map(function (m) {
        return { label: m.major, value: m.major, badge: m.classes.length + ' 个班级' };
      });
    }, document.getElementById('majorGrid'), function (it) {
      state.major = it.value;
      stepClass();
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function stepClass() {
    showStep('stepClass');
    var major = findMajor();
    if (!major) { stepMajor(); return; }
    var items = major.classes.map(function (k) {
      return { label: k.className, value: k.className, badge: k.courses.length + ' 门课' };
    });
    renderList(document.getElementById('classGrid'), items, function (it) {
      state.className = it.value;
      stepSchedule();
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ========== 周次按钮 ==========
  function renderWeekBtns() {
    var wrap = document.getElementById('weekScroll');
    wrap.innerHTML = '';
    var currentWeek = getCurrentWeek();
    var allBtn = document.querySelector('.week-btn[data-week="0"]');
    if (allBtn) {
      allBtn.classList.toggle('active', state.week === 0);
      allBtn.onclick = function () { state.week = 0; stepSchedule(); };
    }
    for (var w = 1; w <= TOTAL_WEEKS; w++) {
      (function (ww) {
        var btn = document.createElement('button');
        btn.className = 'week-btn' + (state.week === ww ? ' active' : '');
        btn.setAttribute('data-week', String(ww));
        btn.textContent = '第' + ww + '周' + (ww === currentWeek ? ' · 本周' : '');
        btn.onclick = function () { state.week = ww; stepSchedule(); };
        wrap.appendChild(btn);
      })(w);
    }
  }

  function renderWeekHint() {
    var hint = document.getElementById('weekHint');
    if (state.week === 0) {
      hint.textContent = '总课表（显示全部课程）';
    } else {
      var start = new Date(START_DATE);
      start.setDate(start.getDate() + (state.week - 1) * 7);
      var end = new Date(start);
      end.setDate(end.getDate() + 6);
      var fmt = function (d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); };
      hint.textContent = '第 ' + state.week + ' 周 · ' + fmt(start) + ' 至 ' + fmt(end);
    }
  }

  function courseInWeek(course, week) {
    if (week === 0) return true;
    if (!course.weeks || course.weeks.length === 0) return false;
    for (var i = 0; i < course.weeks.length; i++) {
      if (course.weeks[i] === week) return true;
    }
    return false;
  }

  function getSlotIndex(c) {
    var ps = c.period_start;
    if (!ps) return 0;
    if (ps <= 2) return 0;
    if (ps <= 4) return 1;
    if (ps <= 6) return 2;
    if (ps <= 8) return 3;
    return 4;
  }

  // ========== 课表网格 ==========
  function stepSchedule() {
    showStep('scheduleCard');
    var cls = findClass();
    if (!cls) { stepClass(); return; }
    var college = findCollege();
    var major = findMajor();

    document.getElementById('scheduleTitle').textContent =
      (college ? college.display + ' · ' : '') +
      (major ? major.major + ' · ' : '') + cls.className;

    renderWeekBtns();
    renderWeekHint();

    var grid = document.getElementById('schedule');
    grid.innerHTML = '';

    // 表头：空 + 7 天
    var corner = document.createElement('div');
    corner.className = 'head empty';
    grid.appendChild(corner);
    for (var d = 0; d < 7; d++) {
      var hd = document.createElement('div');
      hd.className = 'head';
      hd.textContent = DAY_NAMES[d].replace('星期', '周');
      grid.appendChild(hd);
    }

    // 过滤
    var filtered = [];
    for (var i = 0; i < cls.courses.length; i++) {
      if (courseInWeek(cls.courses[i], state.week)) filtered.push(cls.courses[i]);
    }

    // 按 (day, slot) 分桶
    var buckets = {};
    for (var j = 0; j < filtered.length; j++) {
      var c = filtered[j];
      var dayIdx = DAY_NAMES.indexOf(c.day);
      if (dayIdx < 0) continue;
      var slot = getSlotIndex(c);
      var key = dayIdx + '_' + slot;
      if (!buckets[key]) buckets[key] = [];
      buckets[key].push(c);
    }

    // 5 行 × 7 列
    for (var slot = 0; slot < 5; slot++) {
      var lbl = document.createElement('div');
      lbl.className = 'period-label';
      lbl.textContent = PERIOD_LABELS[slot];
      grid.appendChild(lbl);
      for (var dayIdx = 0; dayIdx < 7; dayIdx++) {
        var list = buckets[dayIdx + '_' + slot];
        if (!list || list.length === 0) {
          var empty = document.createElement('div');
          empty.className = 'cell';
          grid.appendChild(empty);
          continue;
        }
        if (list.length === 1) {
          grid.appendChild(makeCourseCell(list[0]));
        } else {
          var stack = document.createElement('div');
          stack.style.cssText = 'display:flex;flex-direction:column;gap:3px;';
          for (var k = 0; k < list.length; k++) {
            stack.appendChild(makeCourseCell(list[k]));
          }
          grid.appendChild(stack);
        }
      }
    }

    // 空状态
    var emptyEl = document.getElementById('scheduleEmpty');
    if (filtered.length === 0) {
      emptyEl.style.display = '';
      grid.style.display = 'none';
    } else {
      emptyEl.style.display = 'none';
      grid.style.display = '';
    }
    // 移除上次的课程详情
    var oldDetail = document.querySelector('.course-detail');
    if (oldDetail) oldDetail.parentNode.removeChild(oldDetail);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function makeCourseCell(c) {
    var cell = document.createElement('div');
    cell.className = 'course-cell color-' + (hashStr(c.name) % 8);
    var weekTxt = c.weeks && c.weeks.length > 0 ? formatWeeks(c.weeks) : '';
    var html = '<div class="cname">' + escapeHtml(c.name) + '</div>';
    if (c.teacher) html += '<div class="cinfo">👤 ' + escapeHtml(c.teacher) + '</div>';
    if (c.location) html += '<div class="cinfo">📍 ' + escapeHtml(c.location) + '</div>';
    if (weekTxt) html += '<div class="cinfo">🗓 ' + escapeHtml(weekTxt) + '</div>';
    cell.innerHTML = html;
    cell.addEventListener('click', function () { showDetail(c); });
    return cell;
  }

  function showDetail(c) {
    var oldDetail = document.querySelector('.course-detail');
    if (oldDetail) oldDetail.parentNode.removeChild(oldDetail);
    var card = document.getElementById('scheduleCard');
    var div = document.createElement('div');
    div.className = 'course-detail';
    var html = '<div class="d-title">' + escapeHtml(c.name) + '</div>';
    if (c.day || c.period) html += '<div class="d-row"><b>时间：</b>' + escapeHtml((c.day || '') + ' ' + (c.period || '')) + '</div>';
    if (c.weeks && c.weeks.length) html += '<div class="d-row"><b>周次：</b>' + escapeHtml(formatWeeks(c.weeks)) + '</div>';
    if (c.location) html += '<div class="d-row"><b>地点：</b>' + escapeHtml(c.location) + '</div>';
    if (c.teacher) html += '<div class="d-row"><b>教师：</b>' + escapeHtml(c.teacher) + '</div>';
    div.innerHTML = html;
    card.appendChild(div);
    setTimeout(function () { div.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, 100);
  }

  // ========== 返回按钮 ==========
  document.getElementById('backToCollege').addEventListener('click', function () {
    state.major = null; state.className = null; stepCollege();
  });
  document.getElementById('backToMajor').addEventListener('click', function () {
    state.className = null; stepMajor();
  });
  document.getElementById('backToClass').addEventListener('click', function () {
    state.week = 0; stepClass();
  });

  // ========== 启动 ==========
  stepCollege();
})();
