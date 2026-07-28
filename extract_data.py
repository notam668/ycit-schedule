# -*- coding: utf-8 -*-
"""
从班级课表.pdf中提取所有课表数据，生成结构化JSON供前端使用
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import re
import pdfplumber

PDF_PATH = r'D:\盐工课表\盐工课表查询系统\班级课表.pdf'
OUTPUT_PATH = r'D:\盐工课表\盐工课表查询系统\schedule_data.js'

# 学院-专业映射（根据盐城工学院实际学院设置）
COLLEGE_MAJOR_MAP = {
    "化学化工学院": ["化工安全工程", "化学工程与工艺", "应用化学", "能源化学", "轻化工程"],
    "材料科学与工程学院": ["材料化学", "材料科学与工程", "高分子材料与工程", "新能源材料与器件", "生物质技术与工程", "金属材料工程"],
    "机械工程学院": ["机械设计制造及其自动化", "机械设计制造及其自动化（国际合作）", "机械设计制造及其自动化（中职高考）", "智能制造工程", "过程装备与控制工程", "智能装备与系统", "机器人工程", "机械大类", "机械电子工程"],
    "电气工程学院": ["电气工程及其自动化", "电气工程及其自动化（国际合作）", "自动化", "电子信息工程", "光电信息科学与工程", "电信大类"],
    "信息工程学院": ["计算机科学与技术", "计算机科学与技术（中职高考）", "软件工程", "网络工程", "数据科学与大数据技术", "人工智能", "智能科学与技术"],
    "土木工程学院": ["土木工程（智慧城市实验班）", "城市地下空间工程（数智实验班）", "给排水科学与工程", "智能建造", "工程管理", "工程管理（中职高考）", "工程管理（3+4）"],
    "海洋与生物工程学院": ["海洋技术", "海洋科学", "水生动物医学", "生物工程", "食品科学与工程", "食品质量与安全", "制药工程"],
    "纺织服装学院": ["纺织工程", "服装设计与工程", "服装设计与工程（中职高考）", "服装与服饰设计"],
    "经济管理学院": ["财务管理", "工商管理", "国际经济与贸易", "会计学", "会计学（中职高考）", "大数据管理与应用", "金融工程", "市场营销(中职高考)", "应急管理", "经管大类", "旅游管理"],
    "设计艺术学院": ["产品设计", "视觉传达设计", "视觉传达设计（中职高考）", "环境设计", "环境设计（中职高考）"],
    "人文社会科学学院": ["汉语言文学", "英语"],
    "数理学院": ["应用统计学", "应用物理学"],
    "环境科学与工程学院": ["环境工程", "环境科学", "环保设备工程"],
    "汽车工程学院": ["车辆工程（与江苏悦达集团有限公司联合培养）", "新能源汽车工程", "新能源汽车工程（中职高考）", "汽车服务工程（3+4）", "交通工程"],
    "新能源学院": ["储能科学与工程", "新能源科学与工程", "能源与动力工程"],
    "应急管理学院": ["应急技术与管理"],
    "智能制造学院": ["智能制造工程（3+4）"],

    "化生材料大类": ["化生材料类"],
    "研究生院": ["Y研究生"],
    "预科教育": ["民族预科（文科）", "民族预科（理科）"],
}

# 时间段定义
TIME_SLOTS = {
    "1-2": {"start": "08:00", "end": "09:40"},
    "3-4": {"start": "10:00", "end": "11:40"},
    "5-6": {"start": "14:00", "end": "15:40"},
    "7-8": {"start": "16:00", "end": "17:40"},
    "9-10": {"start": "19:00", "end": "20:40"},
}

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
WEEKDAY_INDEX = {name: i for i, name in enumerate(WEEKDAYS)}

def find_college(major_name):
    """根据专业名找到对应学院"""
    for college, majors in COLLEGE_MAJOR_MAP.items():
        for m in majors:
            if m in major_name or major_name in m:
                return college
    # 特殊匹配
    if "车辆" in major_name:
        return "汽车工程学院"
    if "研究生" in major_name or major_name.startswith("Y"):
        return "研究生院"
    if "预科" in major_name:
        return "预科教育"
    return "其他"

def parse_schedule_page(page_text):
    """解析单页课表数据"""
    lines = page_text.strip().split('\n')
    if not lines:
        return None
    
    # 提取班级名称（第一行）
    title = lines[0].strip()
    class_match = re.match(r'^([A-Z]\S+?)课表', title)
    if not class_match:
        return None
    class_name = class_match.group(1)
    
    # 提取专业名称
    major = ""
    for line in lines[:3]:
        major_match = re.search(r'专业[：:](.+?)$', line)
        if major_match:
            major = major_match.group(1).strip()
            break
    
    # 如果专业名在第一行中
    if not major:
        major_match2 = re.search(r'专业[：:](.+?)$', title)
        if major_match2:
            major = major_match2.group(1).strip()
    
    if not major:
        # 从班级名推断
        for line in lines:
            if '专业' in line:
                m = re.search(r'专业[：:](.+)', line)
                if m:
                    major = m.group(1).strip()
                    break
    
    # 解析课程信息 - 从文本中提取课程块
    courses = []
    full_text = page_text
    
    # 匹配课程模式: 课程名 + (节次)周次/校区 + /场地/教师
    # 示例: 化工安全导论1\n(1-2节)9-16周/校区:北校区\n/场地:知达楼3J2C306/教师\n:赵垒
    
    # 使用更灵活的方式解析 - 查找所有 (X-X节) 模式
    course_pattern = re.compile(
        r'(?P<course_name>[^\n\d(]+?\d*)\s*\n\s*'
        r'\((?P<sections>\d+-\d+)节\)(?P<weeks>\d+-?\d*)周/校区:(?P<campus>[^\n/]+)\s*\n\s*'
        r'/场地:(?P<location>[^/\n]+)/教师\s*\n?\s*'
        r':?(?P<teacher>[^\n]*)',
        re.MULTILINE
    )
    
    return {
        "class_name": class_name,
        "major": major,
        "raw_text": page_text
    }

def extract_courses_from_table(page):
    """使用表格提取方式获取课程数据"""
    tables = page.extract_tables()
    text = page.extract_text()
    if not text:
        return None
    
    lines = text.strip().split('\n')
    title = lines[0].strip()
    
    class_match = re.match(r'^([A-Z]\S+?)课表', title)
    if not class_match:
        return None
    
    class_name = class_match.group(1)
    
    # 提取专业
    major = ""
    for line in lines[:5]:
        major_match = re.search(r'专业[：:](.+?)$', line)
        if major_match:
            major = major_match.group(1).strip()
            break
    if not major:
        major_match2 = re.search(r'专业[：:]\s*(.+)', title)
        if major_match2:
            major = major_match2.group(1).strip()
    
    # 提取"其他课程"
    other_courses = ""
    for i, line in enumerate(lines):
        if "其他课程" in line:
            other_courses = line
            # 可能跨行
            if i + 1 < len(lines) and not lines[i+1].startswith('1:'):
                other_courses += lines[i+1]
            break
    
    # 解析每天每节的课程
    schedule = {day: {} for day in WEEKDAYS}
    
    # 从原始文本中按位置关系解析课程
    # 课程信息格式: 课程名\n(X-X节)X-X周/校区:XXX\n/场地:XXX/教师\n:XXX
    
    # 重新组织文本，识别课程块
    # 先找到所有节次标记的位置
    current_day = None
    current_section = None
    
    # 使用正则查找所有课程实例
    course_blocks = []
    
    # 匹配模式：课程名后面紧跟(X-X节)
    block_pattern = re.compile(
        r'([^\n()]+?[A-Za-z\u4e00-\u9fff][^\n()]*?)\s*\n\s*'
        r'\((\d+-\d+)节\)(\d+-?\d*)周/校区:([^\n]+)\s*\n\s*'
        r'/场地:([^\n]+?)(?:/教师)?\s*\n?\s*'
        r':?([^\n]*)',
        re.MULTILINE
    )
    
    for match in block_pattern.finditer(text):
        course_name = match.group(1).strip()
        sections = match.group(2)
        weeks = match.group(3)
        campus = match.group(4).strip()
        location = match.group(5).strip()
        teacher = match.group(6).strip()
        
        # 清理课程名
        course_name = re.sub(r'^\d+\s*', '', course_name)
        course_name = re.sub(r'^[上下午晚上]+\s*', '', course_name)
        course_name = course_name.strip()
        
        if course_name and len(course_name) > 1:
            course_blocks.append({
                "name": course_name,
                "sections": sections,
                "weeks": weeks,
                "campus": campus,
                "location": location,
                "teacher": teacher
            })
    
    return {
        "class_name": class_name,
        "major": major,
        "other_courses": other_courses,
        "course_blocks": course_blocks
    }


def parse_full_text_schedule(text):
    """从完整文本中解析课程安排到星期几和节次"""
    lines = text.strip().split('\n')
    
    # 查找标题和专业
    title = lines[0].strip()
    class_match = re.match(r'^([A-Z]\S+?)课表', title)
    if not class_match:
        return None
    class_name = class_match.group(1)
    
    major = ""
    for line in lines[:5]:
        major_match = re.search(r'专业[：:](.+?)$', line)
        if major_match:
            major = major_match.group(1).strip()
            break
    if not major:
        m2 = re.search(r'专业[：:]\s*(.+)', title)
        if m2:
            major = m2.group(1).strip()
    
    # 构建课表数据结构 - 7天 x 5时段
    schedule = {}
    for day in WEEKDAYS:
        schedule[day] = {}
    
    # 其他课程
    other_courses = ""
    for i, line in enumerate(lines):
        if "其他课程" in line:
            other_courses = line
            for j in range(i+1, min(i+3, len(lines))):
                if lines[j].startswith('1:') or '课表' in lines[j]:
                    break
                other_courses += lines[j]
            break
    
    # 解析表格结构
    # 每行格式大致为: 节次号 | 课程1(周一) | 课程2(周二) | ... | 课程7(周日)
    # 但PDF提取的文本不保留表格结构，需要根据位置解析
    
    # 使用表格数据更可靠 - 但此函数用文本
    # 找到每个课程及其时间信息
    
    # 策略：找到所有 "(X-X节)..." 模式，然后关联课程名
    # 课程名在 "(X-X节)" 之前
    
    # 合并所有行为一个文本块来更好地匹配
    full_text = '\n'.join(lines)
    
    return {
        "class_name": class_name,
        "major": major,
        "other_courses": other_courses
    }


def main():
    print("开始从PDF提取课表数据...")
    
    pdf = pdfplumber.open(PDF_PATH)
    all_data = {}  # {学院: {专业: {班级: 课表数据}}}
    class_list = []
    
    page_idx = 0
    while page_idx < len(pdf.pages):
        page = pdf.pages[page_idx]
        text = page.extract_text()
        
        if not text:
            page_idx += 1
            continue
        
        first_line = text.strip().split('\n')[0]
        
        # 跳过非课表页（如图例页）
        if '课表' not in first_line:
            page_idx += 1
            continue
        
        # 如果下一页是图例页，合并两页的内容
        full_text = text
        
        # 解析
        lines = full_text.strip().split('\n')
        title = lines[0].strip()
        
        class_match = re.match(r'^([A-Z]\S+?)课表', title)
        if not class_match:
            page_idx += 1
            continue
        
        class_name = class_match.group(1)
        
        # 提取专业
        major = ""
        for line in lines[:5]:
            major_match = re.search(r'专业[：:](.+?)$', line)
            if major_match:
                major = major_match.group(1).strip()
                break
        if not major:
            m2 = re.search(r'专业[：:]\s*(.+)', title)
            if m2:
                major = m2.group(1).strip()
        
        # 处理车辆工程特殊情况（专业名被截断）
        if '车辆工程' in major and '联合培' in title:
            major = '车辆工程（与江苏悦达集团有限公司联合培养）'
        elif '车辆工程' in major and '联合培' in major:
            major = '车辆工程（与江苏悦达集团有限公司联合培养）'
        
        # 找到学院
        college = find_college(major)
        
        # 提取"其他课程"
        other_courses_text = ""
        for i, line in enumerate(lines):
            if "其他课程" in line:
                other_courses_text = line
                for j in range(i+1, min(i+3, len(lines))):
                    if lines[j].startswith('1:') or '课表' in lines[j]:
                        break
                    other_courses_text += lines[j]
                break
        
        # 解析"其他课程"为列表
        other_courses_list = []
        if other_courses_text:
            oc_text = other_courses_text.replace("其他课程：", "").replace("其他课程:", "")
            # 按分号分隔
            for item in oc_text.split(';'):
                item = item.strip()
                if item and len(item) > 2:
                    other_courses_list.append(item)
        
        # 解析周一到周日每个时间段的课程
        # 利用表格结构提取
        tables = page.extract_tables()
        
        schedule_grid = []  # [{day, section, course_name, weeks, campus, location, teacher}]
        
        if tables:
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    for cell_idx, cell in enumerate(row):
                        if not cell:
                            continue
                        # 查找包含 "(X-X节)" 的单元格
                        if '节)' in cell:
                            # 解析单元格内容
                            cell_lines = cell.split('\n')
                            course_name = ""
                            for cl in cell_lines:
                                cl = cl.strip()
                                if cl and '节)' not in cl and '场地' not in cl and '校区' not in cl and cl not in ['上午', '下午', '晚上'] and not cl.startswith(':') and not cl.startswith('：'):
                                    if not re.match(r'^\d+$', cl) and not re.match(r'^\d{2}:\d{2}$', cl):
                                        course_name = cl
                                        break
                            
                            # 提取节次和周次
                            section_match = re.search(r'\((\d+-\d+)节\)(\d+-?\d*)周', cell)
                            if section_match:
                                sections = section_match.group(1)
                                weeks = section_match.group(2)
                            else:
                                sections = ""
                                weeks = ""
                            
                            # 提取校区
                            campus_match = re.search(r'校区[:：]([^\n/]+)', cell)
                            campus = campus_match.group(1).strip() if campus_match else ""
                            
                            # 提取场地
                            loc_match = re.search(r'场地[:：]([^\n/]+)', cell)
                            location = loc_match.group(1).strip() if loc_match else ""
                            
                            # 提取教师
                            teacher_match = re.search(r'教师\s*\n?\s*[:：]?(.+?)(?:\n|$)', cell)
                            teacher = ""
                            if teacher_match:
                                teacher = teacher_match.group(1).strip()
                            # 也可能在最后一行
                            for cl in reversed(cell_lines):
                                cl = cl.strip()
                                if cl.startswith(':') or cl.startswith('：'):
                                    teacher = cl.lstrip(':：').strip()
                                    break
                            
                            if course_name:
                                schedule_grid.append({
                                    "name": course_name,
                                    "sections": sections,
                                    "weeks": weeks,
                                    "campus": campus,
                                    "location": location,
                                    "teacher": teacher
                                })
        
        # 如果表格提取不够好，用文本解析作为后备
        if not schedule_grid:
            # 文本模式匹配
            course_pattern = re.compile(
                r'([^\n\d()]+?\d*)\s*\n\s*'
                r'\((\d+-\d+)节\)(\d+-?\d*)周/校区:([^\n]+)\s*\n\s*'
                r'/场地:([^\n]+?)(?:/教师)?\s*\n?\s*'
                r':?([^\n]*)',
                re.MULTILINE
            )
            for match in course_pattern.finditer(full_text):
                cname = match.group(1).strip()
                cname = re.sub(r'^\d+\s*', '', cname)
                cname = re.sub(r'^[上下午晚上]+\s*', '', cname)
                cname = cname.strip()
                if cname and len(cname) > 1:
                    schedule_grid.append({
                        "name": cname,
                        "sections": match.group(2),
                        "weeks": match.group(3),
                        "campus": match.group(4).strip(),
                        "location": match.group(5).strip(),
                        "teacher": match.group(6).strip()
                    })
        
        # 确定每门课在星期几 - 通过在文本中查找课程在哪一列
        # 利用page的字符位置信息
        words = page.extract_words()
        
        # 找到星期标题的x坐标范围
        day_columns = {}  # {day_name: (x_min, x_max)}
        for w in words:
            for day in WEEKDAYS:
                if w['text'] == day:
                    day_columns[day] = {'x0': w['x0'], 'x1': w['x1'], 'center': (w['x0'] + w['x1']) / 2}
        
        # 找节次行的y坐标
        section_rows = {}  # {section_num: y_range}
        
        # 为每个课程确定星期几和节次
        # 方法：查找每个 "(X-X节)" 文本的位置
        schedule_by_day = {day: [] for day in WEEKDAYS}
        
        for w in words:
            if '节)' in w['text']:
                # 找到节次标记
                section_match = re.search(r'\((\d+-\d+)节\)', w['text'])
                if not section_match:
                    # 可能被分割了
                    continue
                sections = section_match.group(1)
                wx_center = (w['x0'] + w['x1']) / 2
                
                # 确定在哪一天
                best_day = None
                min_dist = float('inf')
                for day, pos in day_columns.items():
                    dist = abs(wx_center - pos['center'])
                    if dist < min_dist:
                        min_dist = dist
                        best_day = day
                
                if best_day and min_dist < 200:
                    # 找到对应的课程（同一sections的）
                    for course in schedule_grid:
                        if course.get('sections') == sections and 'assigned_day' not in course:
                            course['day'] = best_day
                            course['assigned_day'] = True
                            schedule_by_day[best_day].append(course)
                            break
        
        # 对于没有分配到天的课程，尝试其他方式
        # 通过完整的字符位置分析
        all_chars = page.chars if hasattr(page, 'chars') else []
        
        # 构建最终课表结构
        final_schedule = {day: {} for day in WEEKDAYS}
        
        for day in WEEKDAYS:
            for course in schedule_by_day.get(day, []):
                section_key = course.get('sections', '未知')
                if section_key not in final_schedule[day]:
                    final_schedule[day][section_key] = []
                final_schedule[day][section_key].append({
                    "name": course["name"],
                    "weeks": course.get("weeks", ""),
                    "campus": course.get("campus", ""),
                    "location": course.get("location", ""),
                    "teacher": course.get("teacher", "")
                })
        
        # 同时保留原始课程列表（不论是否成功分配到星期几）
        all_courses = []
        for course in schedule_grid:
            all_courses.append({
                "name": course.get("name", ""),
                "sections": course.get("sections", ""),
                "weeks": course.get("weeks", ""),
                "campus": course.get("campus", ""),
                "location": course.get("location", ""),
                "teacher": course.get("teacher", ""),
                "day": course.get("day", "")
            })
        
        class_data = {
            "class_name": class_name,
            "major": major,
            "college": college,
            "schedule": final_schedule,
            "all_courses": all_courses,
            "other_courses": other_courses_list,
        }
        
        class_list.append(class_data)
        print(f"  已解析: {class_name} - {major} ({college})")
        
        page_idx += 1
    
    pdf.close()
    
    # 构建层级数据结构: 学院 -> 专业 -> 班级
    hierarchy = {}
    for cls in class_list:
        college = cls["college"]
        major = cls["major"]
        class_name = cls["class_name"]
        
        if college not in hierarchy:
            hierarchy[college] = {}
        if major not in hierarchy[college]:
            hierarchy[college][major] = []
        hierarchy[college][major].append(class_name)
    
    # 输出为JS文件（使用变量赋值方式，方便HTML直接引用）
    output = {
        "semester": "2026-2027学年第1学期",
        "hierarchy": hierarchy,
        "schedules": {cls["class_name"]: {
            "major": cls["major"],
            "college": cls["college"],
            "schedule": cls["schedule"],
            "all_courses": cls["all_courses"],
            "other_courses": cls["other_courses"]
        } for cls in class_list}
    }
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write('const SCHEDULE_DATA = ')
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write(';\n')
    
    print(f"\n数据提取完成！")
    print(f"共提取 {len(class_list)} 个班级的课表数据")
    print(f"涵盖 {len(hierarchy)} 个学院")
    print(f"数据已保存到: {OUTPUT_PATH}")
    
    # 打印学院-专业统计
    print("\n学院-专业-班级统计:")
    for college in sorted(hierarchy.keys()):
        majors = hierarchy[college]
        total_classes = sum(len(classes) for classes in majors.values())
        print(f"\n  {college} ({total_classes}个班级):")
        for major in sorted(majors.keys()):
            classes = majors[major]
            print(f"    {major}: {', '.join(classes)}")

if __name__ == '__main__':
    main()
