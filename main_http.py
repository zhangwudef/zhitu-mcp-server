"""
职途智囊 MCP Server - 超星平台专用版本
支持标准 MCP HTTP 协议
"""
import json
import re
from typing import Optional
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn

# ========== 业务数据 ==========
RESUME_CRITERIA = {
    "内容完整性": {"weight": 0.25, "items": ["基本信息", "教育背景", "实习/工作经历", "技能", "证书/荣誉"]},
    "量化成果": {"weight": 0.30, "items": ["数字/百分比", "STAR法则", "结果对比"]},
    "格式规范": {"weight": 0.20, "items": ["一页A4", "字体统一", "排版整洁", "PDF格式"]},
    "关键词匹配": {"weight": 0.15, "items": ["岗位JD匹配", "行业术语", "技术栈关键词"]},
    "专业相关性": {"weight": 0.10, "items": ["经历关联度", "最相关优先"]}
}

MAJOR_CAREER = {
    "大数据技术": ["数据分析师", "Python开发", "大数据运维", "BI工程师", "数据产品助理"],
    "软件技术": ["前端开发", "Java开发", "测试工程师", "技术支持"],
    "计算机网络": ["网络运维", "信息安全", "系统管理员", "云计算"],
    "机电一体化": ["PLC工程师", "自动化工程师", "设备维护", "生产管理"],
    "数控技术": ["数控编程", "CNC操作员", "模具设计", "质检工程师"],
    "工业机器人": ["机器人调试", "自动化系统集成", "智能制造工程师"],
    "电子商务": ["电商运营", "直播运营", "新媒体运营", "跨境电商", "社群运营"],
    "物流管理": ["物流专员", "仓储管理", "供应链助理", "货运代理"],
    "会计": ["会计助理", "审计助理", "税务专员", "出纳", "财务分析"],
    "市场营销": ["销售代表", "市场推广", "品牌策划", "客户经理", "渠道管理"],
    "学前教育": ["幼儿园教师", "早教指导师", "课程顾问", "教育产品运营"],
    "酒店管理": ["前厅接待", "客房管理", "餐饮管理", "宴会策划"],
    "烹饪工艺与营养": ["厨师", "餐饮管理", "食品研发", "营养顾问"],
    "工业设计": ["产品设计师", "UI设计师", "包装设计师", "CAD绘图员"],
    "数字媒体技术": ["视频剪辑", "新媒体运营", "动画设计师", "视觉设计师"]
}

SALARY = {
    "大数据技术": ("6000-10000", "10000-16000", "上升"),
    "软件技术": ("5500-9000", "9000-15000", "稳定"),
    "计算机网络": ("5000-8500", "8000-13000", "稳定"),
    "机电一体化": ("5000-8000", "8000-12000", "制造升级"),
    "电子商务": ("4000-7000", "7000-11000", "直播带动"),
    "会计": ("4000-6500", "6500-10000", "稳定"),
    "数字媒体技术": ("4500-7500", "7500-12000", "上升")
}

INTERVIEW_Q = {
    "行为面试": ["请做自我介绍。", "为什么选择我们公司/岗位？", "你的职业规划是什么？", "介绍一个你最满意的项目经历。", "你遇到的最大困难是什么？怎么解决的？", "描述一次团队冲突经历。", "你的优点和缺点分别是什么？", "如何安排多任务优先级？", "描述压力下完成任务的经验。", "如何看待加班？"],
    "技术面试": ["Python中列表和元组的区别？", "LEFT JOIN和INNER JOIN的区别？", "如何优化慢查询？", "数据清洗常见步骤有哪些？", "pandas和NumPy的区别？", "什么是RFM模型？", "如何处理缺失值和异常值？"],
    "情景面试": ["意见与领导不一致怎么做？", "项目进度落后如何处理？", "被安排不熟悉的任务怎么办？", "同时多个offer怎么选？"]
}

POLICY_DB = {
    "求职补贴": {"政策": "广东省高校毕业生求职创业补贴", "金额": "3000元/人", "条件": "低保/残疾/特困/助学贷款等困难毕业生", "流程": "通过学校就业指导中心申请"},
    "基层就业": {"政策": "高校毕业生基层就业补贴", "金额": "5000-10000元", "条件": "到基层就业并签1年以上劳动合同", "流程": "人社局官网申请"},
    "劳动合同": {"试用期签合同": "入职30日内必须签订书面合同", "试用期上限": "最长6个月(3年以上合同)", "社保": "试用期不缴社保违法", "违约金": "仅培训服务期和竞业限制可约定"},
    "五险一金": {"养老": "单位14%+个人8%，缴满15年退休后领取", "医疗": "单位5.5%+个人2%，门诊住院可报销", "失业": "单位0.8%+个人0.2%，非自愿失业可领", "工伤": "单位缴纳，工伤认定后支付", "生育": "单位缴纳，医疗费报销+生育津贴", "公积金": "双方各5%-12%，可低息贷款买房"},
    "创业贷款": {"政策": "创业担保贷款", "金额": "个人最高50万元", "条件": "高校毕业生创业项目", "福利": "财政贴息"},
    "社保补贴": {"政策": "灵活就业社保补贴", "条件": "灵活就业并缴纳社保的高校毕业生", "金额": "不超过实际缴费2/3"},
    "技能培训": {"政策": "职业技能提升行动", "内容": "免费技能培训+考证补贴", "补贴": "1000-3000元/证书"}
}

ROADMAPS = {
    "数据分析师": {"阶段1_基础(1-2月)": ["Python语法/数据结构/函数", "SQL", "统计学"], "阶段2_核心(2-3月)": ["pandas/NumPy", "可视化", "实战"], "阶段3_进阶(3月+)": ["机器学习", "大数据", "业务思维"], "资源": "B站黑马程序员Python、慕课网数据分析、Kaggle", "考证": "计算机二级Python→软考中级"},
    "Java开发": {"阶段1_基础": ["Java语法/面向对象/集合/IO流"], "阶段2_核心": ["Spring/SpringBoot/MyBatis/MySQL/Redis"], "阶段3_进阶": ["微服务SpringCloud/Docker/项目实战"], "资源": "B站尚硅谷系列、慕课网Java全栈", "考证": "软考中级软件设计师"},
    "前端开发": {"阶段1_基础": ["HTML5/CSS3/JavaScript ES6"], "阶段2_核心": ["Vue.js或React/Node.js/Webpack"], "阶段3_进阶": ["TypeScript/小程序/性能优化"], "资源": "MDN文档、B站coderwhy、慕课网前端", "考证": "软考初级程序员"},
    "PLC工程师": {"阶段1_基础": ["电气基础/电路图识读/低压电器"], "阶段2_核心": ["PLC编程(Siemens S7-1200)/梯形图/HMI"], "阶段3_进阶": ["伺服驱动/变频器/工业网络/项目实战"], "资源": "西门子官方文档、工控论坛", "考证": "电工证→PLC应用工程师"}
}

# ========== 工具实现 ==========
def score_resume_impl(resume_text: str, target_position: str = "未指定", target_industry: str = "未指定") -> dict:
    if len(resume_text) < 20:
        return {"success": False, "error": "简历内容过短"}
    
    details, total = {}, 0.0
    pattern_map = {
        "内容完整性": "基本信息|教育|实习|工作|技能|证书",
        "量化成果": r"\d+%|\d+人|\d+元|增长|提升|降低|倍",
        "关键词匹配": "STAR|数据|项目|团队|成果|负责|优化|完成"
    }
    
    for dim, cfg in RESUME_CRITERIA.items():
        if dim == "格式规范":
            s = 50 if len(resume_text) < 300 else (65 if len(resume_text) > 2000 else 75)
            details[dim] = {"score": s, "weight": cfg["weight"], "suggestion": "控制一页A4，统一字体，导出PDF"}
        elif dim == "专业相关性":
            s = 60 if target_position != "未指定" else 50
            details[dim] = {"score": s, "weight": cfg["weight"], "suggestion": "最相关经历放在显著位置"}
        elif dim in pattern_map:
            hit = bool(re.search(pattern_map[dim], resume_text))
            s = 85 if hit else 40
            details[dim] = {"score": s, "weight": cfg["weight"], "suggestion": f"增强{dim}相关描述"}
        else:
            details[dim] = {"score": 65, "weight": cfg["weight"], "suggestion": f"优化{dim}"}
        total += details[dim]["score"] * cfg["weight"]
    
    total = round(total, 1)
    grade = "优秀" if total >= 90 else ("良好" if total >= 75 else ("合格" if total >= 60 else "不合格"))
    
    return {
        "success": True,
        "total_score": total,
        "grade": grade,
        "target_position": target_position,
        "target_industry": target_industry,
        "dimensions": details,
        "top3_improvements": ["STAR法则改写经历+量化数据", "补全缺失模块", "针对岗位增加匹配关键词"]
    }

def match_career_impl(major: str, skills: Optional[str] = None) -> dict:
    careers = MAJOR_CAREER.get(major, [])
    if not careers:
        for m in MAJOR_CAREER:
            if major in m or m in major:
                careers, major = MAJOR_CAREER[m], m
                break
    
    if not careers:
        return {"success": False, "error": f"未找到专业「{major}」的就业数据"}
    
    sal = SALARY.get(major, ("4500-7500", "7500-12000", "稳定"))
    
    return {
        "success": True,
        "major": major,
        "careers": careers,
        "salary": {"应届生月薪": sal[0], "1-3年月薪": sal[1], "趋势": sal[2]},
        "paths": {"直接就业": "校企合作资源丰富", "专升本": "学历提升拓宽就业面", "考公考编": "计算机/会计类有对口岗", "创业": "顺德创业环境好但风险高"},
        "suggestion": f"推荐方向: {careers[0]}，大湾区应届起薪约{sal[0]}元/月"
    }

def generate_interview_impl(position: str = "通用", question_type: str = "行为面试", count: int = 5) -> dict:
    count = min(max(count, 1), 10)
    
    if question_type == "综合":
        pool = [q for qs in INTERVIEW_Q.values() for q in qs]
    else:
        pool = INTERVIEW_Q.get(question_type, INTERVIEW_Q["行为面试"])
    
    selected = pool[:count] if len(pool) >= count else pool
    tips = {
        "自我介绍": "1-2分钟，突出2-3个与岗位最相关的亮点",
        "最满意": "STAR法则+量化结果",
        "困难": "重点说解决过程",
        "冲突": "展示沟通能力",
        "优点": "用实例支撑",
        "缺点": "真实但可改进",
        "加班": "表达责任感"
    }
    
    qs = []
    for i, q in enumerate(selected):
        tip = next((v for k, v in tips.items() if k in q), "STAR法则+真实经历")
        qs.append({"序号": i+1, "题目": q, "类型": question_type, "答题要点": tip})
    
    return {
        "success": True,
        "position": position,
        "questions": qs,
        "tip": "使用STAR法则(情境→任务→行动→结果)，每题1-2分钟"
    }

def generate_radar_impl(scores_json: str) -> dict:
    try:
        scores = json.loads(scores_json)
    except:
        return {"success": False, "error": "JSON格式错误"}
    
    dims = ["专业技能", "通用能力", "学习能力", "职业素养", "行业认知"]
    vals = [min(max(scores.get(d, 0), 0), 5) for d in dims]
    mn, mx = dims[vals.index(min(vals))], dims[vals.index(max(vals))]
    
    sugg = {
        "专业技能": "实训课程+在线项目+职业证书",
        "通用能力": "社团活动+小组项目",
        "学习能力": "跨学科技能+每周自学",
        "职业素养": "实习+企业参观",
        "行业认知": "阅读行业报告+关注招聘趋势"
    }
    
    return {
        "success": True,
        "labels": dims,
        "values": vals,
        "max_value": 5,
        "strength": mx,
        "weakness": mn,
        "weakness_suggestion": sugg.get(mn, "针对性提升"),
        "overall": round(sum(vals)/5, 1)
    }

def query_policy_impl(keyword: str) -> dict:
    for k, v in POLICY_DB.items():
        if keyword in k or k in keyword:
            return {"success": True, "keyword": keyword, "matched": k, "policy": v}
    
    return {"success": False, "error": f"未找到「{keyword}」", "available": list(POLICY_DB.keys())}

def plan_roadmap_impl(target_job: str, current_level: str = "入门") -> dict:
    rm = ROADMAPS.get(target_job)
    if not rm:
        return {"success": False, "error": f"暂无「{target_job}」的学习路线", "available": list(ROADMAPS.keys())}
    
    stages = {k: v for k, v in rm.items() if k.startswith("阶段")}
    
    return {
        "success": True,
        "target_job": target_job,
        "current_level": current_level,
        "stages": stages,
        "resources": rm.get("资源", ""),
        "certification": rm.get("考证", ""),
        "estimated_time": "6-8个月(入门→可求职)"
    }

# ========== 工具注册 ==========
TOOLS_MAP = {
    "score_resume": {
        "name": "score_resume",
        "description": "五维评分诊断简历",
        "function": score_resume_impl,
        "parameters": {
            "resume_text": {"type": "string", "description": "简历文本内容", "required": True},
            "target_position": {"type": "string", "description": "目标岗位", "required": False},
            "target_industry": {"type": "string", "description": "目标行业", "required": False}
        }
    },
    "match_career": {
        "name": "match_career",
        "description": "根据专业匹配就业方向",
        "function": match_career_impl,
        "parameters": {
            "major": {"type": "string", "description": "专业名称", "required": True},
            "skills": {"type": "string", "description": "掌握技能", "required": False}
        }
    },
    "generate_interview_questions": {
        "name": "generate_interview_questions",
        "description": "生成模拟面试题目",
        "function": generate_interview_impl,
        "parameters": {
            "position": {"type": "string", "description": "目标岗位", "required": False},
            "question_type": {"type": "string", "description": "题目类型(行为面试/技术面试/情景面试/综合)", "required": False},
            "count": {"type": "integer", "description": "题目数量", "required": False}
        }
    },
    "generate_radar_chart": {
        "name": "generate_radar_chart",
        "description": "根据能力自评生成雷达图数据",
        "function": generate_radar_impl,
        "parameters": {
            "scores_json": {"type": "string", "description": "JSON格式的能力评分", "required": True}
        }
    },
    "query_employment_policy": {
        "name": "query_employment_policy",
        "description": "查询就业政策",
        "function": query_policy_impl,
        "parameters": {
            "keyword": {"type": "string", "description": "查询关键词", "required": True}
        }
    },
    "plan_skill_roadmap": {
        "name": "plan_skill_roadmap",
        "description": "生成分阶段技能学习路线",
        "function": plan_roadmap_impl,
        "parameters": {
            "target_job": {"type": "string", "description": "目标岗位", "required": True},
            "current_level": {"type": "string", "description": "当前水平", "required": False}
        }
    }
}

# ========== API 端点 ==========
async def health_check(request):
    return JSONResponse({
        "status": "healthy",
        "service": "职途智囊MCP Server",
        "version": "1.0.0",
        "protocol": "http-json"
    })

async def list_tools(request):
    tools = []
    for name, info in TOOLS_MAP.items():
        tools.append({
            "name": info["name"],
            "description": info["description"],
            "parameters": info["parameters"]
        })
    return JSONResponse({"tools": tools})

async def invoke_tool(request):
    body = await request.json()
    tool_name = body.get("name")
    arguments = body.get("arguments", {})
    
    if tool_name not in TOOLS_MAP:
        return JSONResponse({"error": f"工具不存在: {tool_name}"}, status_code=404)
    
    tool_info = TOOLS_MAP[tool_name]
    try:
        result = tool_info["function"](**arguments)
        return JSONResponse({
            "name": tool_name,
            "result": result
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def score_resume(request):
    body = await request.json()
    result = score_resume_impl(**body)
    return JSONResponse(result)

async def match_career(request):
    body = await request.json()
    result = match_career_impl(**body)
    return JSONResponse(result)

async def generate_interview(request):
    body = await request.json()
    result = generate_interview_impl(**body)
    return JSONResponse(result)

async def generate_radar(request):
    body = await request.json()
    result = generate_radar_impl(**body)
    return JSONResponse(result)

async def query_policy(request):
    body = await request.json()
    result = query_policy_impl(**body)
    return JSONResponse(result)

async def plan_roadmap(request):
    body = await request.json()
    result = plan_roadmap_impl(**body)
    return JSONResponse(result)

# ========== 创建应用 ==========
app = Starlette(
    debug=True,
    routes=[
        Route("/health", health_check),
        Route("/tools", list_tools),
        Route("/list_tools", list_tools),
        Route("/invoke", invoke_tool, methods=["POST"]),
        Route("/api/invoke", invoke_tool, methods=["POST"]),
        Route("/api/score_resume", score_resume, methods=["POST"]),
        Route("/api/match_career", match_career, methods=["POST"]),
        Route("/api/generate_interview", generate_interview, methods=["POST"]),
        Route("/api/generate_radar", generate_radar, methods=["POST"]),
        Route("/api/query_policy", query_policy, methods=["POST"]),
        Route("/api/plan_roadmap", plan_roadmap, methods=["POST"]),
    ]
)

# ========== 启动 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("职途智囊 MCP Server v1.0")
    print("专为超星平台设计 - HTTP JSON 协议")
    print("=" * 60)
    print("服务地址: http://localhost:8080")
    print("协议类型: HTTP + JSON")
    print("=" * 60)
    print("可用工具:")
    for i, (name, info) in enumerate(TOOLS_MAP.items(), 1):
        print(f"  {i}. {name} - {info['description']}")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
