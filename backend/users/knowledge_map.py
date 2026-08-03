data_structure_map = {
  "nodes": [
    {"id":"2","name":"数组","type":"structure","difficulty":1},
    {"id":"3","name":"链表","type":"structure","difficulty":1},
    {"id":"4","name":"栈","type":"structure","difficulty":1},
    {"id":"5","name":"队列","type":"structure","difficulty":1},
    {"id":"6","name":"哈希表","type":"structure","difficulty":2},
    {"id":"7","name":"堆","type":"structure","difficulty":2},

    {"id":"8","name":"树","type":"structure","difficulty":1},
    {"id":"9","name":"二叉树","type":"structure","difficulty":1},
    {"id":"10","name":"二叉搜索树","type":"structure","difficulty":2},
    {"id":"11","name":"AVL树","type":"structure","difficulty":3},
    {"id":"12","name":"红黑树","type":"structure","difficulty":4},
    {"id":"13","name":"Trie树","type":"structure","difficulty":3},
    {"id":"14","name":"B树","type":"structure","difficulty":4},
    {"id":"15","name":"B+树","type":"structure","difficulty":4},

    {"id":"16","name":"图","type":"structure","difficulty":2},
    {"id":"17","name":"DFS","type":"algorithm","difficulty":2},
    {"id":"18","name":"BFS","type":"algorithm","difficulty":2},
    {"id":"19","name":"Dijkstra","type":"algorithm","difficulty":4},
    {"id":"20","name":"拓扑排序","type":"algorithm","difficulty":3},

    {"id":"21","name":"优先队列","type":"concept","difficulty":2},
    {"id":"22","name":"回溯算法","type":"concept","difficulty":4},
    {"id":"23","name":"动态规划","type":"concept","difficulty":5},

    {"id":"24","name":"时间复杂度","type":"concept","difficulty":1},
    {"id":"25","name":"空间复杂度","type":"concept","difficulty":1},

    {"id":"26","name":"TreeMap","type":"application","difficulty":3},
    {"id":"27","name":"数据库索引","type":"application","difficulty":3},
    {"id":"28","name":"搜索引擎","type":"application","difficulty":3},
    {"id":"29","name":"缓存系统","type":"application","difficulty":3},
    {"id":"30","name":"最短路径问题","type":"application","difficulty":3},

    {"id":"31","name":"KMP算法","type":"algorithm","difficulty":3},
    {"id":"32","name":"AC自动机","type":"algorithm","difficulty":5},
    {"id":"33","name":"字符串哈希","type":"algorithm","difficulty":2},

    {"id":"34","name":"归并排序","type":"algorithm","difficulty":2},
    {"id":"35","name":"快速排序","type":"algorithm","difficulty":2},
    {"id":"36","name":"堆排序","type":"algorithm","difficulty":2},
    {"id":"37","name":"计数排序","type":"algorithm","difficulty":2},
    {"id":"38","name":"桶排序","type":"algorithm","difficulty":2},
    {"id":"39","name":"基数排序","type":"algorithm","difficulty":3},
    {"id":"40","name":"排序稳定性","type":"concept","difficulty":2},
    {"id":"41","name":"内部排序","type":"concept","difficulty":1},
    {"id":"42","name":"外部排序","type":"concept","difficulty":3},

    {"id":"43","name":"并查集","type":"structure","difficulty":3},
    {"id":"44","name":"线段树","type":"structure","difficulty":4},
    {"id":"45","name":"树状数组","type":"structure","difficulty":4},
    {"id":"46","name":"跳表","type":"structure","difficulty":3},
    {"id":"47","name":"布隆过滤器","type":"structure","difficulty":3},

    {"id":"48","name":"Floyd算法","type":"algorithm","difficulty":3},
    {"id":"49","name":"Prim算法","type":"algorithm","difficulty":3},
    {"id":"50","name":"Kruskal算法","type":"algorithm","difficulty":3},
    {"id":"51","name":"Tarjan算法","type":"algorithm","difficulty":5},
    {"id":"52","name":"最大流","type":"algorithm","difficulty":5},

    {"id":"53","name":"递归与分治","type":"concept","difficulty":2},
    {"id":"54","name":"贪心算法","type":"concept","difficulty":3}
  ],

  "relations": [
    {"source":"8","target":"9","type":"contains"},
    {"source":"9","target":"10","type":"contains"},
    {"source":"10","target":"11","type":"contains"},
    {"source":"10","target":"12","type":"contains"},
    {"source":"8","target":"13","type":"contains"},
    {"source":"8","target":"14","type":"contains"},
    {"source":"14","target":"15","type":"contains"},

    {"source":"17","target":"16","type":"used_in"},
    {"source":"17","target":"8","type":"used_in"},
    {"source":"17","target":"22","type":"related_to"},

    {"source":"18","target":"16","type":"used_in"},
    {"source":"18","target":"8","type":"used_in"},

    {"source":"19","target":"16","type":"used_in"},
    {"source":"19","target":"30","type":"solves"},

    {"source":"20","target":"16","type":"used_in"},

    {"source":"7","target":"21","type":"implements"},
    {"source":"21","target":"7","type":"implemented_by"},

    {"source":"12","target":"26","type":"used_by"},
    {"source":"15","target":"27","type":"used_by"},
    {"source":"13","target":"28","type":"used_by"},
    {"source":"6","target":"29","type":"used_by"},

    {"source":"10","target":"9","type":"prerequisite"},
    {"source":"11","target":"10","type":"prerequisite"},
    {"source":"12","target":"10","type":"prerequisite"},
    {"source":"15","target":"14","type":"prerequisite"},

    {"source":"17","target":"18","type":"related_to"},
    {"source":"17","target":"19","type":"prerequisite"},
    {"source":"18","target":"19","type":"prerequisite"},

    {"source":"24","target":"2","type":"evaluates"},
    {"source":"24","target":"3","type":"evaluates"},
    {"source":"24","target":"6","type":"evaluates"},
    {"source":"24","target":"7","type":"evaluates"},

    {"source":"25","target":"2","type":"evaluates"},
    {"source":"25","target":"3","type":"evaluates"},
    {"source":"25","target":"16","type":"evaluates"},

    {"source":"31","target":"3","type":"used_in"},
    {"source":"32","target":"3","type":"used_in"},
    {"source":"32","target":"13","type":"used_in"},
    {"source":"33","target":"6","type":"used_in"},

    {"source":"34","target":"53","type":"prerequisite"},
    {"source":"35","target":"53","type":"prerequisite"},
    {"source":"35","target":"54","type":"prerequisite"},
    {"source":"36","target":"7","type":"used_in"},
    {"source":"37","target":"41","type":"implements"},
    {"source":"38","target":"41","type":"implements"},
    {"source":"39","target":"41","type":"implements"},
    {"source":"42","target":"37","type":"prerequisite"},
    {"source":"42","target":"38","type":"prerequisite"},
    {"source":"40","target":"34","type":"evaluates"},
    {"source":"40","target":"35","type":"evaluates"},
    {"source":"40","target":"36","type":"evaluates"},

    {"source":"43","target":"16","type":"used_in"},
    {"source":"44","target":"8","type":"used_in"},
    {"source":"44","target":"16","type":"used_in"},
    {"source":"45","target":"8","type":"used_in"},
    {"source":"45","target":"44","type":"related_to"},
    {"source":"46","target":"5","type":"implements"},
    {"source":"47","target":"6","type":"related_to"},

    {"source":"48","target":"16","type":"used_in"},
    {"source":"48","target":"19","type":"related_to"},
    {"source":"49","target":"16","type":"used_in"},
    {"source":"49","target":"50","type":"related_to"},
    {"source":"50","target":"43","type":"used_in"},
    {"source":"50","target":"16","type":"used_in"},
    {"source":"51","target":"16","type":"used_in"},
    {"source":"51","target":"17","type":"prerequisite"},
    {"source":"52","target":"16","type":"used_in"},
    {"source":"52","target":"43","type":"used_in"},

    {"source":"53","target":"17","type":"used_in"},
    {"source":"53","target":"22","type":"used_in"},
    {"source":"53","target":"23","type":"used_in"},
    {"source":"54","target":"49","type":"used_in"},
    {"source":"54","target":"50","type":"used_in"}
  ]
}

cybersecurity_map = {
  "nodes": [
    {"id":"2","name":"对称加密","type":"concept","difficulty":2},
    {"id":"3","name":"非对称加密","type":"concept","difficulty":3},
    {"id":"4","name":"哈希函数","type":"concept","difficulty":2},
    {"id":"5","name":"数字签名","type":"concept","difficulty":3},

    {"id":"6","name":"SSL/TLS","type":"protocol","difficulty":3},
    {"id":"7","name":"HTTPS","type":"protocol","difficulty":2},
    {"id":"8","name":"SSH","type":"protocol","difficulty":2},
    {"id":"9","name":"VPN","type":"technology","difficulty":3},

    {"id":"10","name":"防火墙","type":"defense","difficulty":2},
    {"id":"11","name":"入侵检测","type":"defense","difficulty":3},
    {"id":"12","name":"WAF","type":"defense","difficulty":3},
    {"id":"13","name":"零信任","type":"defense","difficulty":3},

    {"id":"14","name":"网络钓鱼","type":"attack","difficulty":1},
    {"id":"15","name":"XSS","type":"attack","difficulty":2},
    {"id":"16","name":"SQL注入","type":"attack","difficulty":2},
    {"id":"17","name":"CSRF","type":"attack","difficulty":2},
    {"id":"18","name":"中间人攻击","type":"attack","difficulty":3},
    {"id":"19","name":"DoS/DDoS","type":"attack","difficulty":2},
    {"id":"20","name":"ARP欺骗","type":"attack","difficulty":3},
    {"id":"21","name":"DNS安全","type":"defense","difficulty":3},

    {"id":"22","name":"安全协议","type":"concept","difficulty":2},
    {"id":"23","name":"渗透测试","type":"method","difficulty":4},
    {"id":"24","name":"安全逆向","type":"method","difficulty":5},
    {"id":"25","name":"恶意软件","type":"malware","difficulty":3}
  ],

  "relations": [
    {"source":"2","target":"6","type":"used_in"},
    {"source":"2","target":"8","type":"used_in"},
    {"source":"3","target":"5","type":"used_in"},
    {"source":"3","target":"6","type":"used_in"},
    {"source":"3","target":"8","type":"used_in"},
    {"source":"4","target":"5","type":"used_in"},
    {"source":"4","target":"25","type":"used_in"},

    {"source":"5","target":"6","type":"prerequisite"},
    {"source":"6","target":"7","type":"prerequisite"},
    {"source":"7","target":"8","type":"related_to"},

    {"source":"9","target":"2","type":"used_in"},
    {"source":"9","target":"3","type":"used_in"},
    {"source":"9","target":"6","type":"used_in"},

    {"source":"10","target":"13","type":"related_to"},
    {"source":"11","target":"10","type":"prerequisite"},
    {"source":"12","target":"10","type":"related_to"},
    {"source":"13","target":"6","type":"used_in"},
    {"source":"13","target":"9","type":"used_in"},

    {"source":"14","target":"18","type":"related_to"},
    {"source":"15","target":"12","type":"used_in"},
    {"source":"16","target":"12","type":"used_in"},
    {"source":"17","target":"7","type":"related_to"},
    {"source":"18","target":"6","type":"used_in"},
    {"source":"18","target":"8","type":"used_in"},
    {"source":"19","target":"20","type":"related_to"},
    {"source":"20","target":"10","type":"prerequisite"},
    {"source":"21","target":"19","type":"related_to"},

    {"source":"22","target":"6","type":"contains"},
    {"source":"22","target":"7","type":"contains"},
    {"source":"22","target":"8","type":"contains"},
    {"source":"22","target":"9","type":"contains"},

    {"source":"23","target":"14","type":"used_in"},
    {"source":"23","target":"15","type":"used_in"},
    {"source":"23","target":"16","type":"used_in"},
    {"source":"23","target":"17","type":"used_in"},
    {"source":"23","target":"18","type":"used_in"},
    {"source":"23","target":"19","type":"used_in"},
    {"source":"23","target":"20","type":"used_in"},
    {"source":"23","target":"25","type":"used_in"},

    {"source":"24","target":"25","type":"used_in"},
    {"source":"24","target":"4","type":"used_in"},

    {"source":"25","target":"4","type":"used_in"},
    {"source":"25","target":"14","type":"related_to"}
  ]
}

iot_map = {
  "nodes": [
    {"id":"2","name":"传感器","type":"device","difficulty":1},
    {"id":"3","name":"RFID","type":"device","difficulty":2},
    {"id":"4","name":"嵌入式系统","type":"system","difficulty":2},
    {"id":"5","name":"MCU","type":"hardware","difficulty":2},
    {"id":"6","name":"SoC","type":"hardware","difficulty":3},
    {"id":"7","name":"实时操作系统","type":"software","difficulty":3},
    {"id":"8","name":"边缘计算","type":"technology","difficulty":3},
    {"id":"9","name":"云平台","type":"infrastructure","difficulty":2},

    {"id":"10","name":"MQTT","type":"protocol","difficulty":3},
    {"id":"11","name":"CoAP","type":"protocol","difficulty":3},
    {"id":"12","name":"LwM2M","type":"protocol","difficulty":4},
    {"id":"13","name":"NB-IoT","type":"communication","difficulty":3},
    {"id":"14","name":"LoRa","type":"communication","difficulty":3},
    {"id":"15","name":"WiFi","type":"communication","difficulty":2},
    {"id":"16","name":"Bluetooth","type":"communication","difficulty":2},
    {"id":"17","name":"ZigBee","type":"communication","difficulty":3},

    {"id":"18","name":"通信协议","type":"concept","difficulty":2},
    {"id":"19","name":"设备管理OTA","type":"technology","difficulty":3},
    {"id":"20","name":"数字孪生","type":"technology","difficulty":4},
    {"id":"21","name":"智能网关","type":"device","difficulty":3}
  ],

  "relations": [
    {"source":"4","target":"5","type":"contains"},
    {"source":"4","target":"6","type":"contains"},
    {"source":"4","target":"7","type":"contains"},
    {"source":"5","target":"6","type":"prerequisite"},
    {"source":"7","target":"5","type":"prerequisite"},

    {"source":"2","target":"21","type":"used_in"},
    {"source":"3","target":"21","type":"used_in"},
    {"source":"21","target":"8","type":"related_to"},
    {"source":"21","target":"9","type":"related_to"},

    {"source":"18","target":"10","type":"contains"},
    {"source":"18","target":"11","type":"contains"},
    {"source":"18","target":"12","type":"contains"},
    {"source":"18","target":"13","type":"contains"},
    {"source":"18","target":"14","type":"contains"},
    {"source":"18","target":"15","type":"contains"},
    {"source":"18","target":"16","type":"contains"},
    {"source":"18","target":"17","type":"contains"},

    {"source":"10","target":"8","type":"used_in"},
    {"source":"10","target":"9","type":"used_in"},
    {"source":"11","target":"8","type":"used_in"},
    {"source":"12","target":"10","type":"prerequisite"},
    {"source":"13","target":"18","type":"used_in"},
    {"source":"14","target":"18","type":"used_in"},
    {"source":"15","target":"18","type":"used_in"},
    {"source":"16","target":"18","type":"used_in"},
    {"source":"17","target":"18","type":"used_in"},

    {"source":"8","target":"9","type":"related_to"},
    {"source":"9","target":"20","type":"used_in"},
    {"source":"20","target":"2","type":"used_in"},
    {"source":"20","target":"4","type":"used_in"},

    {"source":"19","target":"4","type":"used_in"},
    {"source":"19","target":"21","type":"used_in"},

    {"source":"8","target":"21","type":"used_in"},
    {"source":"9","target":"10","type":"prerequisite"},
    {"source":"9","target":"11","type":"prerequisite"}
  ]
}

electrical_automation_map = {
  # Python 编程语言知识图谱 —— 替换原"电气自动化"内容
  # 81 节点 / 14 个 type 类别 / ~80 条 prerequisite/used_in/related_to 关系
  # node id 用 py_NNN 前缀, 跟其他学科的数字 id 不会撞
  "nodes": [
    # ========== 语言基础 foundation (12) ==========
    {"id":"py_001","name":"词法与标识符","type":"foundation","difficulty":1},
    {"id":"py_002","name":"数据类型与字面量","type":"foundation","difficulty":1},
    {"id":"py_003","name":"运算符与表达式","type":"foundation","difficulty":1},
    {"id":"py_004","name":"控制流 (if/for/while)","type":"foundation","difficulty":1},
    {"id":"py_005","name":"函数 def 与作用域","type":"foundation","difficulty":2},
    {"id":"py_006","name":"lambda 与高阶函数","type":"functional","difficulty":2},
    {"id":"py_007","name":"闭包与装饰器","type":"functional","difficulty":3},
    {"id":"py_008","name":"模块与包 import","type":"foundation","difficulty":2},
    {"id":"py_009","name":"异常与 traceback","type":"foundation","difficulty":2},
    {"id":"py_010","name":"上下文管理器 with","type":"foundation","difficulty":3},
    {"id":"py_011","name":"推导式 (list/dict/set)","type":"foundation","difficulty":2},
    {"id":"py_012","name":"模式匹配 match-case","type":"foundation","difficulty":2},

    # ========== 面向对象 object (8) ==========
    {"id":"py_020","name":"类与对象","type":"object","difficulty":2},
    {"id":"py_021","name":"继承与 MRO","type":"object","difficulty":3},
    {"id":"py_022","name":"魔术方法 (dunder)","type":"object","difficulty":3},
    {"id":"py_023","name":"描述符协议","type":"object","difficulty":4},
    {"id":"py_024","name":"元类 metaclass","type":"object","difficulty":5},
    {"id":"py_025","name":"抽象基类 ABC","type":"object","difficulty":3},
    {"id":"py_026","name":"property/slot/classmethod","type":"object","difficulty":3},
    {"id":"py_027","name":"dataclass / attrs","type":"object","difficulty":2},

    # ========== 类型系统 type (5) ==========
    {"id":"py_030","name":"鸭子类型 / EAFP","type":"type","difficulty":2},
    {"id":"py_031","name":"typing 模块","type":"type","difficulty":3},
    {"id":"py_032","name":"Protocol / TypeVar","type":"type","difficulty":4},
    {"id":"py_033","name":"泛型 Generic","type":"type","difficulty":3},
    {"id":"py_034","name":"introspection 内省","type":"type","difficulty":3},

    # ========== 并发与异步 concurrency (8) ==========
    {"id":"py_040","name":"GIL 全局解释器锁","type":"concurrency","difficulty":3},
    {"id":"py_041","name":"threading 多线程","type":"concurrency","difficulty":3},
    {"id":"py_042","name":"Lock / RLock / Semaphore","type":"concurrency","difficulty":3},
    {"id":"py_043","name":"multiprocessing","type":"concurrency","difficulty":3},
    {"id":"py_044","name":"concurrent.futures","type":"concurrency","difficulty":3},
    {"id":"py_045","name":"asyncio 事件循环","type":"concurrency","difficulty":4},
    {"id":"py_046","name":"async/await 协程","type":"concurrency","difficulty":3},
    {"id":"py_047","name":"Task / Future / gather","type":"concurrency","difficulty":4},

    # ========== 内存管理 memory (5) ==========
    {"id":"py_050","name":"引用计数","type":"memory","difficulty":3},
    {"id":"py_051","name":"垃圾回收 gc","type":"memory","difficulty":3},
    {"id":"py_052","name":"弱引用 weakref","type":"memory","difficulty":4},
    {"id":"py_053","name":"pymalloc 内存池","type":"memory","difficulty":5},
    {"id":"py_054","name":"内存视图 memoryview","type":"memory","difficulty":3},

    # ========== 数据结构 data-structure (7) ==========
    {"id":"py_060","name":"list / tuple 动态数组","type":"data-structure","difficulty":2},
    {"id":"py_061","name":"dict / set 哈希表","type":"data-structure","difficulty":3},
    {"id":"py_062","name":"collections.deque","type":"data-structure","difficulty":2},
    {"id":"py_063","name":"heapq 堆队列","type":"data-structure","difficulty":3},
    {"id":"py_064","name":"bisect 二分查找","type":"data-structure","difficulty":2},
    {"id":"py_065","name":"OrderedDict / Counter","type":"data-structure","difficulty":2},
    {"id":"py_066","name":"array / 连续内存","type":"data-structure","difficulty":3},

    # ========== 迭代器协议 iteration (4) ==========
    {"id":"py_070","name":"迭代器协议 iter/next","type":"iteration","difficulty":2},
    {"id":"py_071","name":"生成器函数 yield","type":"iteration","difficulty":3},
    {"id":"py_072","name":"yield from 委托生成器","type":"iteration","difficulty":4},
    {"id":"py_073","name":"itertools 工具集","type":"iteration","difficulty":3},

    # ========== IO 与系统 io (5) ==========
    {"id":"py_080","name":"文件 I/O","type":"io","difficulty":1},
    {"id":"py_081","name":"pathlib 路径","type":"io","difficulty":2},
    {"id":"py_082","name":"subprocess 子进程","type":"io","difficulty":3},
    {"id":"py_083","name":"socket 网络编程","type":"io","difficulty":3},
    {"id":"py_084","name":"selectors IO 多路复用","type":"io","difficulty":4},

    # ========== 标准库 stdlib (8) ==========
    {"id":"py_090","name":"json / pickle","type":"stdlib","difficulty":2},
    {"id":"py_091","name":"logging 日志","type":"stdlib","difficulty":2},
    {"id":"py_092","name":"unittest 测试","type":"stdlib","difficulty":2},
    {"id":"py_093","name":"argparse CLI","type":"stdlib","difficulty":2},
    {"id":"py_094","name":"re 正则","type":"stdlib","difficulty":3},
    {"id":"py_095","name":"datetime / zoneinfo","type":"stdlib","difficulty":2},
    {"id":"py_096","name":"hashlib / hmac","type":"stdlib","difficulty":3},
    {"id":"py_097","name":"secrets 安全随机","type":"stdlib","difficulty":2},

    # ========== 性能与调试 perf (4) ==========
    {"id":"py_100","name":"cProfile 性能分析","type":"perf","difficulty":3},
    {"id":"py_101","name":"tracemalloc 内存追踪","type":"perf","difficulty":4},
    {"id":"py_102","name":"dis 字节码反汇编","type":"perf","difficulty":4},
    {"id":"py_103","name":"timeit 性能基准","type":"perf","difficulty":2},

    # ========== C 扩展 interop (3) ==========
    {"id":"py_110","name":"ctypes 调用 C","type":"interop","difficulty":4},
    {"id":"py_111","name":"CFFI 高级 C 互操作","type":"interop","difficulty":5},
    {"id":"py_112","name":"Cython 编译扩展","type":"interop","difficulty":4},

    # ========== 工具链 tool (5) ==========
    {"id":"py_120","name":"pip / venv / uv","type":"tool","difficulty":1},
    {"id":"py_121","name":"pytest 测试框架","type":"tool","difficulty":2},
    {"id":"py_122","name":"mypy / pyright 类型检查","type":"tool","difficulty":3},
    {"id":"py_123","name":"ruff / black / isort","type":"tool","difficulty":2},
    {"id":"py_124","name":"pyproject.toml / Poetry","type":"tool","difficulty":2},

    # ========== 生态 ecosystem (4) ==========
    {"id":"py_130","name":"Django 全栈","type":"ecosystem","difficulty":3},
    {"id":"py_131","name":"FastAPI 异步 Web","type":"ecosystem","difficulty":3},
    {"id":"py_132","name":"NumPy / Pandas","type":"ecosystem","difficulty":3},
    {"id":"py_133","name":"Jupyter / IPython","type":"ecosystem","difficulty":2},

    # ========== 部署 deploy (3) ==========
    {"id":"py_140","name":"WSGI / ASGI 协议","type":"deploy","difficulty":3},
    {"id":"py_141","name":"Gunicorn / uvicorn","type":"deploy","difficulty":3},
    {"id":"py_142","name":"Docker 化 Python","type":"deploy","difficulty":3},
  ],

  "relations": [
    # ──────── 语言基础 prerequisite 链 ────────
    {"source":"py_001","target":"py_002","type":"prerequisite"},
    {"source":"py_002","target":"py_003","type":"prerequisite"},
    {"source":"py_003","target":"py_004","type":"prerequisite"},
    {"source":"py_004","target":"py_005","type":"prerequisite"},
    {"source":"py_005","target":"py_006","type":"prerequisite"},
    {"source":"py_005","target":"py_007","type":"prerequisite"},
    {"source":"py_005","target":"py_008","type":"prerequisite"},
    {"source":"py_002","target":"py_009","type":"prerequisite"},
    {"source":"py_005","target":"py_010","type":"prerequisite"},
    {"source":"py_002","target":"py_011","type":"prerequisite"},
    {"source":"py_004","target":"py_012","type":"prerequisite"},

    # ──────── 面向对象链 ────────
    {"source":"py_001","target":"py_020","type":"prerequisite"},
    {"source":"py_005","target":"py_020","type":"prerequisite"},
    {"source":"py_020","target":"py_021","type":"prerequisite"},
    {"source":"py_020","target":"py_022","type":"prerequisite"},
    {"source":"py_022","target":"py_023","type":"prerequisite"},
    {"source":"py_023","target":"py_024","type":"prerequisite"},
    {"source":"py_020","target":"py_025","type":"prerequisite"},
    {"source":"py_022","target":"py_026","type":"prerequisite"},
    {"source":"py_020","target":"py_027","type":"prerequisite"},

    # ──────── 类型系统 ────────
    {"source":"py_020","target":"py_030","type":"prerequisite"},
    {"source":"py_030","target":"py_031","type":"prerequisite"},
    {"source":"py_031","target":"py_032","type":"prerequisite"},
    {"source":"py_031","target":"py_033","type":"prerequisite"},
    {"source":"py_020","target":"py_034","type":"prerequisite"},

    # ──────── 并发与异步 ────────
    {"source":"py_005","target":"py_041","type":"prerequisite"},
    {"source":"py_020","target":"py_041","type":"used_in"},
    {"source":"py_041","target":"py_042","type":"prerequisite"},
    {"source":"py_041","target":"py_043","type":"related_to"},
    {"source":"py_041","target":"py_044","type":"related_to"},
    {"source":"py_005","target":"py_046","type":"prerequisite"},
    {"source":"py_046","target":"py_045","type":"used_in"},
    {"source":"py_046","target":"py_047","type":"prerequisite"},
    {"source":"py_041","target":"py_040","type":"related_to"},
    {"source":"py_040","target":"py_043","type":"related_to"},

    # ──────── 内存管理 ────────
    {"source":"py_001","target":"py_050","type":"prerequisite"},
    {"source":"py_020","target":"py_050","type":"prerequisite"},
    {"source":"py_050","target":"py_051","type":"prerequisite"},
    {"source":"py_050","target":"py_052","type":"prerequisite"},
    {"source":"py_050","target":"py_053","type":"related_to"},
    {"source":"py_080","target":"py_054","type":"prerequisite"},

    # ──────── 数据结构 (Python-specific) ────────
    {"source":"py_002","target":"py_060","type":"prerequisite"},
    {"source":"py_060","target":"py_061","type":"prerequisite"},
    {"source":"py_060","target":"py_062","type":"prerequisite"},
    {"source":"py_063","target":"py_062","type":"related_to"},
    {"source":"py_060","target":"py_063","type":"used_in"},
    {"source":"py_060","target":"py_064","type":"used_in"},
    {"source":"py_061","target":"py_065","type":"prerequisite"},
    {"source":"py_060","target":"py_066","type":"related_to"},

    # ──────── 迭代器协议 ────────
    {"source":"py_020","target":"py_070","type":"prerequisite"},
    {"source":"py_070","target":"py_071","type":"prerequisite"},
    {"source":"py_071","target":"py_072","type":"prerequisite"},
    {"source":"py_070","target":"py_073","type":"prerequisite"},

    # ──────── IO 与系统 ────────
    {"source":"py_002","target":"py_080","type":"prerequisite"},
    {"source":"py_080","target":"py_081","type":"prerequisite"},
    {"source":"py_080","target":"py_082","type":"prerequisite"},
    {"source":"py_041","target":"py_083","type":"prerequisite"},
    {"source":"py_083","target":"py_084","type":"prerequisite"},

    # ──────── 标准库 ────────
    {"source":"py_080","target":"py_090","type":"used_in"},
    {"source":"py_009","target":"py_091","type":"used_in"},
    {"source":"py_020","target":"py_092","type":"used_in"},
    {"source":"py_005","target":"py_093","type":"used_in"},
    {"source":"py_003","target":"py_094","type":"prerequisite"},
    {"source":"py_050","target":"py_095","type":"prerequisite"},
    {"source":"py_050","target":"py_096","type":"used_in"},
    {"source":"py_096","target":"py_097","type":"prerequisite"},

    # ──────── 性能与调试 ────────
    {"source":"py_005","target":"py_100","type":"used_in"},
    {"source":"py_050","target":"py_101","type":"prerequisite"},
    {"source":"py_020","target":"py_102","type":"prerequisite"},
    {"source":"py_005","target":"py_103","type":"used_in"},

    # ──────── C 扩展 ────────
    {"source":"py_001","target":"py_110","type":"prerequisite"},
    {"source":"py_110","target":"py_111","type":"prerequisite"},
    {"source":"py_050","target":"py_112","type":"prerequisite"},

    # ──────── 工具链 ────────
    {"source":"py_008","target":"py_120","type":"prerequisite"},
    {"source":"py_020","target":"py_092","type":"used_in"},
    {"source":"py_092","target":"py_121","type":"related_to"},
    {"source":"py_031","target":"py_122","type":"prerequisite"},
    {"source":"py_120","target":"py_123","type":"used_in"},
    {"source":"py_008","target":"py_124","type":"prerequisite"},

    # ──────── 生态 ────────
    {"source":"py_020","target":"py_130","type":"prerequisite"},
    {"source":"py_046","target":"py_131","type":"prerequisite"},
    {"source":"py_060","target":"py_132","type":"prerequisite"},
    {"source":"py_001","target":"py_133","type":"prerequisite"},

    # ──────── 部署 ────────
    {"source":"py_005","target":"py_140","type":"prerequisite"},
    {"source":"py_130","target":"py_141","type":"used_in"},
    {"source":"py_131","target":"py_141","type":"used_in"},
    {"source":"py_080","target":"py_142","type":"prerequisite"},
  ]
}

mechanical_design_map = {
  # 操作系统 (Operating System) 知识图谱 —— 替换原"机械设计"内容
  # 81 节点 / 14 个 type 类别 / ~80 条关系
  # node id 用 os_NNN 前缀, 跟其他学科 id 不会撞
  "nodes": [
    # ========== 进程与线程 process (10) ==========
    {"id":"os_001","name":"进程基础 (PCB / 状态)","type":"process","difficulty":1},
    {"id":"os_002","name":"线程与协程","type":"process","difficulty":2},
    {"id":"os_003","name":"进程调度 (CFS / O(1))","type":"process","difficulty":3},
    {"id":"os_004","name":"实时调度 / 优先级反转","type":"process","difficulty":4},
    {"id":"os_005","name":"进程创建 fork / exec","type":"process","difficulty":2},
    {"id":"os_006","name":"进程终止与回收 wait","type":"process","difficulty":2},
    {"id":"os_007","name":"守护进程 / init","type":"process","difficulty":2},
    {"id":"os_008","name":"进程组 / 会话","type":"process","difficulty":3},
    {"id":"os_009","name":"nice / cgroups 优先级","type":"process","difficulty":3},
    {"id":"os_010","name":"PID 命名空间","type":"process","difficulty":2},

    # ========== 内存管理 memory (8) ==========
    {"id":"os_011","name":"虚拟内存","type":"memory","difficulty":2},
    {"id":"os_012","name":"分页 (Paging)","type":"memory","difficulty":2},
    {"id":"os_013","name":"分段 (Segmentation)","type":"memory","difficulty":3},
    {"id":"os_014","name":"TLB 与多级页表","type":"memory","difficulty":3},
    {"id":"os_015","name":"页面置换算法 (LRU / Clock)","type":"memory","difficulty":3},
    {"id":"os_016","name":"缺页中断处理","type":"memory","difficulty":3},
    {"id":"os_017","name":"内存映射 mmap","type":"memory","difficulty":3},
    {"id":"os_018","name":"OOM Killer 与 swap","type":"memory","difficulty":3},

    # ========== 文件系统 fs (10) ==========
    {"id":"os_020","name":"VFS 虚拟文件系统","type":"fs","difficulty":3},
    {"id":"os_021","name":"inode 与 dentry","type":"fs","difficulty":3},
    {"id":"os_022","name":"块设备与字符设备","type":"fs","difficulty":2},
    {"id":"os_023","name":"文件描述符 (fd)","type":"fs","difficulty":2},
    {"id":"os_024","name":"ext4 / xfs / btrfs","type":"fs","difficulty":3},
    {"id":"os_025","name":"日志 (Journaling)","type":"fs","difficulty":3},
    {"id":"os_026","name":"文件系统快照","type":"fs","difficulty":4},
    {"id":"os_027","name":"配额与 ACL","type":"fs","difficulty":3},
    {"id":"os_028","name":"tmpfs / procfs / sysfs","type":"fs","difficulty":3},
    {"id":"os_029","name":"NFS / SMB 网络文件系统","type":"fs","difficulty":3},

    # ========== 进程同步 sync (8) ==========
    {"id":"os_030","name":"互斥锁 mutex","type":"sync","difficulty":2},
    {"id":"os_031","name":"自旋锁 spinlock","type":"sync","difficulty":3},
    {"id":"os_032","name":"信号量 semaphore","type":"sync","difficulty":2},
    {"id":"os_033","name":"读写锁 rwlock","type":"sync","difficulty":3},
    {"id":"os_034","name":"RCU 读拷贝更新","type":"sync","difficulty":5},
    {"id":"os_035","name":"屏障 memory barrier","type":"sync","difficulty":4},
    {"id":"os_036","name":"futex 用户态锁","type":"sync","difficulty":4},
    {"id":"os_037","name":"死锁 / 活锁 / 饥饿","type":"sync","difficulty":3},

    # ========== 进程间通信 ipc (6) ==========
    {"id":"os_040","name":"pipe / FIFO","type":"ipc","difficulty":2},
    {"id":"os_041","name":"Unix domain socket","type":"ipc","difficulty":2},
    {"id":"os_042","name":"TCP / UDP socket","type":"ipc","difficulty":2},
    {"id":"os_043","name":"共享内存 shm","type":"ipc","difficulty":3},
    {"id":"os_044","name":"信号 signal","type":"ipc","difficulty":3},
    {"id":"os_045","name":"POSIX 消息队列 mqueue","type":"ipc","difficulty":3},

    # ========== IO 子系统 io (5) ==========
    {"id":"os_050","name":"块 IO 调度 (CFQ / Deadline)","type":"io","difficulty":3},
    {"id":"os_051","name":"零拷贝 sendfile / splice","type":"io","difficulty":3},
    {"id":"os_052","name":"io_uring 异步 IO","type":"io","difficulty":4},
    {"id":"os_053","name":"DMA 与中断处理","type":"io","difficulty":3},
    {"id":"os_054","name":"设备驱动模型","type":"io","difficulty":3},

    # ========== 网络协议栈 net (6) ==========
    {"id":"os_060","name":"TCP 三握四挥","type":"net","difficulty":3},
    {"id":"os_061","name":"select / poll / epoll","type":"net","difficulty":3},
    {"id":"os_062","name":"Nagle 算法 / 延迟确认","type":"net","difficulty":3},
    {"id":"os_063","name":"拥塞控制 (CUBIC / BBR)","type":"net","difficulty":4},
    {"id":"os_064","name":"Netfilter / iptables","type":"net","difficulty":4},
    {"id":"os_065","name":"TCP 协议栈调优","type":"net","difficulty":4},

    # ========== 安全 security (5) ==========
    {"id":"os_070","name":"Linux capability","type":"security","difficulty":3},
    {"id":"os_071","name":"seccomp 系统调用过滤","type":"security","difficulty":4},
    {"id":"os_072","name":"SELinux / AppArmor","type":"security","difficulty":4},
    {"id":"os_073","name":"ASLR / KASLR / PIE","type":"security","difficulty":3},
    {"id":"os_074","name":"CFI 控制流完整性","type":"security","difficulty":4},

    # ========== 虚拟化 virt (6) ==========
    {"id":"os_080","name":"KVM 内核虚拟化","type":"virt","difficulty":3},
    {"id":"os_081","name":"QEMU / KVM 用户态","type":"virt","difficulty":3},
    {"id":"os_082","name":"Xen hypervisor","type":"virt","difficulty":4},
    {"id":"os_083","name":"硬件辅助 VT-x / AMD-V","type":"virt","difficulty":3},
    {"id":"os_084","name":"Docker / OCI 容器","type":"virt","difficulty":2},
    {"id":"os_085","name":"cgroup / namespace","type":"virt","difficulty":3},

    # ========== 启动 boot (5) ==========
    {"id":"os_090","name":"BIOS / UEFI 固件","type":"boot","difficulty":3},
    {"id":"os_091","name":"GRUB / bootloader","type":"boot","difficulty":3},
    {"id":"os_092","name":"initramfs / dracut","type":"boot","difficulty":3},
    {"id":"os_093","name":"systemd init 流程","type":"boot","difficulty":2},
    {"id":"os_094","name":"systemd unit 依赖","type":"boot","difficulty":3},

    # ========== 内核子系统 kernel (6) ==========
    {"id":"os_100","name":"Linux 内核架构 (宏内核)","type":"kernel","difficulty":2},
    {"id":"os_101","name":"eBPF / bpf() syscall","type":"kernel","difficulty":4},
    {"id":"os_102","name":"kernel module 加载","type":"kernel","difficulty":3},
    {"id":"os_103","name":"系统调用 (syscall)","type":"kernel","difficulty":2},
    {"id":"os_104","name":"中断 / 异常 / 软中断","type":"kernel","difficulty":3},
    {"id":"os_105","name":"CPU 调度域 (sched_domain)","type":"kernel","difficulty":4},

    # ========== 性能分析 perf (6) ==========
    {"id":"os_110","name":"perf 性能分析","type":"perf","difficulty":3},
    {"id":"os_111","name":"ftrace 内核跟踪","type":"perf","difficulty":4},
    {"id":"os_112","name":"bpftrace 高级跟踪","type":"perf","difficulty":4},
    {"id":"os_113","name":"strace 系统调用跟踪","type":"perf","difficulty":2},
    {"id":"os_114","name":"vmstat / iostat / mpstat","type":"perf","difficulty":2},
    {"id":"os_115","name":"火焰图 (flame graph)","type":"perf","difficulty":3},
  ],

  "relations": [
    # ──────── 进程与线程 ────────
    {"source":"os_001","target":"os_002","type":"prerequisite"},
    {"source":"os_002","target":"os_003","type":"prerequisite"},
    {"source":"os_003","target":"os_004","type":"prerequisite"},
    {"source":"os_001","target":"os_005","type":"prerequisite"},
    {"source":"os_005","target":"os_006","type":"prerequisite"},
    {"source":"os_001","target":"os_007","type":"used_in"},
    {"source":"os_005","target":"os_008","type":"prerequisite"},
    {"source":"os_008","target":"os_007","type":"related_to"},
    {"source":"os_002","target":"os_009","type":"prerequisite"},
    {"source":"os_002","target":"os_010","type":"prerequisite"},

    # ──────── 内存管理 ────────
    {"source":"os_011","target":"os_012","type":"prerequisite"},
    {"source":"os_012","target":"os_013","type":"prerequisite"},
    {"source":"os_012","target":"os_014","type":"prerequisite"},
    {"source":"os_012","target":"os_015","type":"prerequisite"},
    {"source":"os_015","target":"os_016","type":"prerequisite"},
    {"source":"os_011","target":"os_017","type":"prerequisite"},
    {"source":"os_015","target":"os_018","type":"prerequisite"},

    # ──────── 文件系统 ────────
    {"source":"os_001","target":"os_023","type":"prerequisite"},
    {"source":"os_020","target":"os_021","type":"prerequisite"},
    {"source":"os_022","target":"os_024","type":"prerequisite"},
    {"source":"os_020","target":"os_024","type":"prerequisite"},
    {"source":"os_021","target":"os_024","type":"prerequisite"},
    {"source":"os_024","target":"os_025","type":"prerequisite"},
    {"source":"os_025","target":"os_026","type":"prerequisite"},
    {"source":"os_024","target":"os_027","type":"prerequisite"},
    {"source":"os_020","target":"os_028","type":"used_in"},
    {"source":"os_024","target":"os_029","type":"used_in"},

    # ──────── 进程同步 ────────
    {"source":"os_001","target":"os_030","type":"prerequisite"},
    {"source":"os_030","target":"os_031","type":"prerequisite"},
    {"source":"os_030","target":"os_032","type":"related_to"},
    {"source":"os_030","target":"os_033","type":"prerequisite"},
    {"source":"os_033","target":"os_034","type":"prerequisite"},
    {"source":"os_030","target":"os_035","type":"prerequisite"},
    {"source":"os_032","target":"os_036","type":"prerequisite"},
    {"source":"os_030","target":"os_037","type":"prerequisite"},

    # ──────── 进程间通信 ────────
    {"source":"os_002","target":"os_040","type":"prerequisite"},
    {"source":"os_040","target":"os_041","type":"prerequisite"},
    {"source":"os_041","target":"os_042","type":"prerequisite"},
    {"source":"os_002","target":"os_043","type":"prerequisite"},
    {"source":"os_002","target":"os_044","type":"prerequisite"},
    {"source":"os_040","target":"os_045","type":"prerequisite"},

    # ──────── IO 子系统 ────────
    {"source":"os_022","target":"os_050","type":"prerequisite"},
    {"source":"os_050","target":"os_051","type":"prerequisite"},
    {"source":"os_050","target":"os_052","type":"prerequisite"},
    {"source":"os_022","target":"os_053","type":"prerequisite"},
    {"source":"os_022","target":"os_054","type":"prerequisite"},

    # ──────── 网络协议栈 ────────
    {"source":"os_042","target":"os_060","type":"prerequisite"},
    {"source":"os_060","target":"os_061","type":"prerequisite"},
    {"source":"os_060","target":"os_062","type":"prerequisite"},
    {"source":"os_060","target":"os_063","type":"prerequisite"},
    {"source":"os_060","target":"os_064","type":"prerequisite"},
    {"source":"os_060","target":"os_065","type":"prerequisite"},

    # ──────── 安全 ────────
    {"source":"os_001","target":"os_070","type":"prerequisite"},
    {"source":"os_070","target":"os_071","type":"prerequisite"},
    {"source":"os_070","target":"os_072","type":"prerequisite"},
    {"source":"os_011","target":"os_073","type":"prerequisite"},
    {"source":"os_073","target":"os_074","type":"prerequisite"},

    # ──────── 虚拟化 ────────
    {"source":"os_100","target":"os_080","type":"prerequisite"},
    {"source":"os_080","target":"os_081","type":"prerequisite"},
    {"source":"os_080","target":"os_082","type":"related_to"},
    {"source":"os_100","target":"os_083","type":"prerequisite"},
    {"source":"os_080","target":"os_084","type":"prerequisite"},
    {"source":"os_084","target":"os_085","type":"prerequisite"},

    # ──────── 启动 ────────
    {"source":"os_100","target":"os_090","type":"prerequisite"},
    {"source":"os_090","target":"os_091","type":"prerequisite"},
    {"source":"os_091","target":"os_092","type":"prerequisite"},
    {"source":"os_092","target":"os_093","type":"prerequisite"},
    {"source":"os_093","target":"os_094","type":"prerequisite"},

    # ──────── 内核子系统 ────────
    {"source":"os_001","target":"os_100","type":"prerequisite"},
    {"source":"os_100","target":"os_101","type":"prerequisite"},
    {"source":"os_100","target":"os_102","type":"prerequisite"},
    {"source":"os_002","target":"os_103","type":"prerequisite"},
    {"source":"os_002","target":"os_104","type":"prerequisite"},
    {"source":"os_003","target":"os_105","type":"prerequisite"},

    # ──────── 性能分析 ────────
    {"source":"os_100","target":"os_110","type":"used_in"},
    {"source":"os_110","target":"os_111","type":"prerequisite"},
    {"source":"os_111","target":"os_112","type":"prerequisite"},
    {"source":"os_103","target":"os_113","type":"prerequisite"},
    {"source":"os_022","target":"os_114","type":"prerequisite"},
    {"source":"os_110","target":"os_115","type":"prerequisite"},
  ]
}

advanced_math_map = {
  # 软件工程 (Software Engineering) 知识图谱 —— 替换原"高等数学"内容
  # 81 节点 / 14 个 type 类别 / ~80 条关系
  # node id 用 se_NNN 前缀, 跟其他学科 id 不会撞
  "nodes": [
    # ========== 软件生命周期 lifecycle (6) ==========
    {"id":"se_001","name":"软件生命周期模型","type":"lifecycle","difficulty":1},
    {"id":"se_002","name":"瀑布模型","type":"lifecycle","difficulty":1},
    {"id":"se_003","name":"迭代与增量开发","type":"lifecycle","difficulty":2},
    {"id":"se_004","name":"V 模型 / 双 V 模型","type":"lifecycle","difficulty":2},
    {"id":"se_005","name":"螺旋模型","type":"lifecycle","difficulty":2},
    {"id":"se_006","name":"敏捷宣言与原则","type":"lifecycle","difficulty":2},

    # ========== 需求工程 requirements (8) ==========
    {"id":"se_010","name":"需求层次 (业务/用户/功能)","type":"requirements","difficulty":2},
    {"id":"se_011","name":"EARS 需求语法","type":"requirements","difficulty":3},
    {"id":"se_012","name":"用户故事 (User Story)","type":"requirements","difficulty":2},
    {"id":"se_013","name":"Use Case 用例","type":"requirements","difficulty":2},
    {"id":"se_014","name":"验收标准 AC","type":"requirements","difficulty":2},
    {"id":"se_015","name":"NFR 非功能需求","type":"requirements","difficulty":3},
    {"id":"se_016","name":"需求优先级 (MoSCoW)","type":"requirements","difficulty":2},
    {"id":"se_017","name":"需求追踪矩阵","type":"requirements","difficulty":3},

    # ========== 设计原则 principles (6) ==========
    {"id":"se_020","name":"SOLID 五大原则","type":"principles","difficulty":3},
    {"id":"se_021","name":"DRY / KISS / YAGNI","type":"principles","difficulty":1},
    {"id":"se_022","name":"GRASP 通用职责分配","type":"principles","difficulty":3},
    {"id":"se_023","name":"关注点分离 (SoC)","type":"principles","difficulty":2},
    {"id":"se_024","name":"信息专家 / 创建者模式","type":"principles","difficulty":3},
    {"id":"se_025","name":"高内聚低耦合","type":"principles","difficulty":2},

    # ========== 设计模式 patterns (10) ==========
    {"id":"se_030","name":"GoF 23 模式综述","type":"patterns","difficulty":3},
    {"id":"se_031","name":"单例 / 工厂方法","type":"patterns","difficulty":2},
    {"id":"se_032","name":"建造者 / 原型","type":"patterns","difficulty":2},
    {"id":"se_033","name":"适配器 / 装饰器","type":"patterns","difficulty":2},
    {"id":"se_034","name":"代理模式","type":"patterns","difficulty":2},
    {"id":"se_035","name":"外观 / 组合","type":"patterns","difficulty":2},
    {"id":"se_036","name":"观察者 / 策略","type":"patterns","difficulty":3},
    {"id":"se_037","name":"模板方法 / 状态","type":"patterns","difficulty":3},
    {"id":"se_038","name":"责任链 / 命令","type":"patterns","difficulty":3},
    {"id":"se_039","name":"发布订阅 / 中介者","type":"patterns","difficulty":3},

    # ========== 架构模式 architecture (8) ==========
    {"id":"se_040","name":"MVC / MVP / MVVM","type":"architecture","difficulty":2},
    {"id":"se_041","name":"分层架构","type":"architecture","difficulty":2},
    {"id":"se_042","name":"六边形 (端口适配器)","type":"architecture","difficulty":3},
    {"id":"se_043","name":"洋葱架构 / Clean","type":"architecture","difficulty":3},
    {"id":"se_044","name":"微服务架构","type":"architecture","difficulty":3},
    {"id":"se_045","name":"事件驱动 / CQRS / Event Sourcing","type":"architecture","difficulty":4},
    {"id":"se_046","name":"微内核 / 插件架构","type":"architecture","difficulty":3},
    {"id":"se_047","name":"Serverless / BaaS","type":"architecture","difficulty":3},

    # ========== 测试 testing (8) ==========
    {"id":"se_050","name":"测试金字塔","type":"testing","difficulty":2},
    {"id":"se_051","name":"单元测试 (Jest/Pytest)","type":"testing","difficulty":2},
    {"id":"se_052","name":"集成测试","type":"testing","difficulty":2},
    {"id":"se_053","name":"E2E 测试 (Playwright)","type":"testing","difficulty":3},
    {"id":"se_054","name":"契约测试 (Pact)","type":"testing","difficulty":4},
    {"id":"se_055","name":"性能测试 (k6/JMeter)","type":"testing","difficulty":3},
    {"id":"se_056","name":"安全测试 / 渗透测试","type":"testing","difficulty":3},
    {"id":"se_057","name":"TDD 红绿重构","type":"testing","difficulty":3},

    # ========== CI/CD 与 DevOps cicd (8) ==========
    {"id":"se_060","name":"CI 持续集成","type":"cicd","difficulty":2},
    {"id":"se_061","name":"CD 持续部署","type":"cicd","difficulty":2},
    {"id":"se_062","name":"GitOps / ArgoCD","type":"cicd","difficulty":3},
    {"id":"se_063","name":"蓝绿部署 / 金丝雀发布","type":"cicd","difficulty":3},
    {"id":"se_064","name":"Feature Flag 灰度","type":"cicd","difficulty":3},
    {"id":"se_065","name":"IaC 基础设施即代码 (Terraform)","type":"cicd","difficulty":3},
    {"id":"se_066","name":"可观测性 (Logging/Tracing/Metrics)","type":"cicd","difficulty":3},
    {"id":"se_067","name":"SLO / SLA / Error Budget","type":"cicd","difficulty":3},

    # ========== 代码质量 quality (6) ==========
    {"id":"se_070","name":"Code Review 评审","type":"quality","difficulty":2},
    {"id":"se_071","name":"静态分析 (SonarQube)","type":"quality","difficulty":2},
    {"id":"se_072","name":"圈复杂度 / 可维护指数","type":"quality","difficulty":3},
    {"id":"se_073","name":"重构技法 (Fowler)","type":"quality","difficulty":3},
    {"id":"se_074","name":"技术债管理","type":"quality","difficulty":3},
    {"id":"se_075","name":"Linter / Formatter 配置","type":"quality","difficulty":1},

    # ========== 估算与度量 metrics (5) ==========
    {"id":"se_080","name":"故事点 / Planning Poker","type":"metrics","difficulty":2},
    {"id":"se_081","name":"速率 (Velocity) / 燃尽图","type":"metrics","difficulty":2},
    {"id":"se_082","name":"COCOMO 估算","type":"metrics","difficulty":3},
    {"id":"se_083","name":"Function Point 功能点","type":"metrics","difficulty":3},
    {"id":"se_084","name":"DORA 四个指标","type":"metrics","difficulty":3},

    # ========== 敏捷方法 agile (5) ==========
    {"id":"se_090","name":"Scrum 框架","type":"agile","difficulty":2},
    {"id":"se_091","name":"Kanban 看板方法","type":"agile","difficulty":2},
    {"id":"se_092","name":"XP 极限编程 (结对 / TDD)","type":"agile","difficulty":3},
    {"id":"se_093","name":"Scrumban / Scrumbut","type":"agile","difficulty":3},
    {"id":"se_094","name":"规模化敏捷 (SAFe / LeSS)","type":"agile","difficulty":3},

    # ========== 配置管理 configmgmt (4) ==========
    {"id":"se_100","name":"Git Flow 分支模型","type":"configmgmt","difficulty":2},
    {"id":"se_101","name":"Trunk-based Development","type":"configmgmt","difficulty":2},
    {"id":"se_102","name":"GitHub Flow / GitLab Flow","type":"configmgmt","difficulty":2},
    {"id":"se_103","name":"Monorepo 策略","type":"configmgmt","difficulty":3},

    # ========== 风险管理 risk (4) ==========
    {"id":"se_110","name":"FMEA 失效模式分析","type":"risk","difficulty":3},
    {"id":"se_111","name":"风险矩阵 / 概率影响图","type":"risk","difficulty":2},
    {"id":"se_112","name":"风险登记册 (Risk Register)","type":"risk","difficulty":2},
    {"id":"se_113","name":"缓解策略 / 应急预案","type":"risk","difficulty":3},

    # ========== 过程改进 process (3) ==========
    {"id":"se_120","name":"CMMI 5 级成熟度","type":"process","difficulty":3},
    {"id":"se_121","name":"ISO 9001 / ISO 27001","type":"process","difficulty":3},
    {"id":"se_122","name":"PSP / TSP 个人/团队过程","type":"process","difficulty":3},
  ],

  "relations": [
    # ──────── 软件生命周期 ────────
    {"source":"se_001","target":"se_002","type":"prerequisite"},
    {"source":"se_002","target":"se_003","type":"prerequisite"},
    {"source":"se_002","target":"se_004","type":"related_to"},
    {"source":"se_003","target":"se_005","type":"prerequisite"},
    {"source":"se_006","target":"se_001","type":"prerequisite"},

    # ──────── 需求工程 ────────
    {"source":"se_001","target":"se_010","type":"prerequisite"},
    {"source":"se_010","target":"se_011","type":"prerequisite"},
    {"source":"se_010","target":"se_012","type":"prerequisite"},
    {"source":"se_010","target":"se_013","type":"related_to"},
    {"source":"se_012","target":"se_014","type":"prerequisite"},
    {"source":"se_010","target":"se_015","type":"prerequisite"},
    {"source":"se_012","target":"se_016","type":"prerequisite"},
    {"source":"se_012","target":"se_017","type":"prerequisite"},

    # ──────── 设计原则 ────────
    {"source":"se_021","target":"se_020","type":"prerequisite"},
    {"source":"se_020","target":"se_022","type":"prerequisite"},
    {"source":"se_022","target":"se_023","type":"prerequisite"},
    {"source":"se_021","target":"se_024","type":"prerequisite"},
    {"source":"se_020","target":"se_025","type":"prerequisite"},

    # ──────── 设计模式 ────────
    {"source":"se_022","target":"se_030","type":"prerequisite"},
    {"source":"se_030","target":"se_031","type":"prerequisite"},
    {"source":"se_030","target":"se_032","type":"prerequisite"},
    {"source":"se_030","target":"se_033","type":"prerequisite"},
    {"source":"se_030","target":"se_034","type":"prerequisite"},
    {"source":"se_030","target":"se_035","type":"prerequisite"},
    {"source":"se_030","target":"se_036","type":"prerequisite"},
    {"source":"se_030","target":"se_037","type":"prerequisite"},
    {"source":"se_030","target":"se_038","type":"prerequisite"},
    {"source":"se_030","target":"se_039","type":"prerequisite"},

    # ──────── 架构模式 ────────
    {"source":"se_030","target":"se_040","type":"prerequisite"},
    {"source":"se_020","target":"se_041","type":"prerequisite"},
    {"source":"se_041","target":"se_042","type":"prerequisite"},
    {"source":"se_042","target":"se_043","type":"prerequisite"},
    {"source":"se_041","target":"se_044","type":"prerequisite"},
    {"source":"se_044","target":"se_045","type":"prerequisite"},
    {"source":"se_041","target":"se_046","type":"prerequisite"},
    {"source":"se_041","target":"se_047","type":"related_to"},

    # ──────── 测试 ────────
    {"source":"se_001","target":"se_050","type":"prerequisite"},
    {"source":"se_050","target":"se_051","type":"prerequisite"},
    {"source":"se_051","target":"se_052","type":"prerequisite"},
    {"source":"se_052","target":"se_053","type":"prerequisite"},
    {"source":"se_044","target":"se_054","type":"prerequisite"},
    {"source":"se_044","target":"se_055","type":"prerequisite"},
    {"source":"se_001","target":"se_056","type":"prerequisite"},
    {"source":"se_057","target":"se_051","type":"prerequisite"},

    # ──────── CI/CD 与 DevOps ────────
    {"source":"se_051","target":"se_060","type":"prerequisite"},
    {"source":"se_060","target":"se_061","type":"prerequisite"},
    {"source":"se_061","target":"se_062","type":"prerequisite"},
    {"source":"se_061","target":"se_063","type":"related_to"},
    {"source":"se_061","target":"se_064","type":"prerequisite"},
    {"source":"se_061","target":"se_065","type":"prerequisite"},
    {"source":"se_061","target":"se_066","type":"prerequisite"},
    {"source":"se_061","target":"se_067","type":"prerequisite"},

    # ──────── 代码质量 ────────
    {"source":"se_001","target":"se_070","type":"prerequisite"},
    {"source":"se_070","target":"se_071","type":"prerequisite"},
    {"source":"se_020","target":"se_072","type":"prerequisite"},
    {"source":"se_020","target":"se_073","type":"prerequisite"},
    {"source":"se_070","target":"se_074","type":"prerequisite"},
    {"source":"se_022","target":"se_075","type":"prerequisite"},

    # ──────── 估算与度量 ────────
    {"source":"se_006","target":"se_080","type":"prerequisite"},
    {"source":"se_080","target":"se_081","type":"prerequisite"},
    {"source":"se_001","target":"se_082","type":"prerequisite"},
    {"source":"se_001","target":"se_083","type":"prerequisite"},
    {"source":"se_080","target":"se_084","type":"prerequisite"},

    # ──────── 敏捷方法 ────────
    {"source":"se_006","target":"se_090","type":"prerequisite"},
    {"source":"se_006","target":"se_091","type":"prerequisite"},
    {"source":"se_090","target":"se_092","type":"related_to"},
    {"source":"se_090","target":"se_093","type":"related_to"},
    {"source":"se_090","target":"se_094","type":"prerequisite"},

    # ──────── 配置管理 ────────
    {"source":"se_001","target":"se_100","type":"prerequisite"},
    {"source":"se_100","target":"se_101","type":"prerequisite"},
    {"source":"se_100","target":"se_102","type":"related_to"},
    {"source":"se_044","target":"se_103","type":"prerequisite"},

    # ──────── 风险管理 ────────
    {"source":"se_001","target":"se_110","type":"prerequisite"},
    {"source":"se_110","target":"se_111","type":"prerequisite"},
    {"source":"se_110","target":"se_112","type":"prerequisite"},
    {"source":"se_112","target":"se_113","type":"prerequisite"},

    # ──────── 过程改进 ────────
    {"source":"se_070","target":"se_120","type":"prerequisite"},
    {"source":"se_070","target":"se_121","type":"related_to"},
    {"source":"se_070","target":"se_122","type":"prerequisite"},
  ]
}

artificial_intelligence_map = {
  "nodes": [
    {"id":"2","name":"机器学习","type":"field","difficulty":1},
    {"id":"3","name":"深度学习","type":"field","difficulty":2},
    {"id":"4","name":"监督学习","type":"paradigm","difficulty":2},
    {"id":"5","name":"无监督学习","type":"paradigm","difficulty":2},
    {"id":"6","name":"半监督学习","type":"paradigm","difficulty":3},

    {"id":"7","name":"线性回归","type":"algorithm","difficulty":2},
    {"id":"8","name":"决策树","type":"algorithm","difficulty":2},
    {"id":"9","name":"支持向量机","type":"algorithm","difficulty":4},
    {"id":"10","name":"K近邻","type":"algorithm","difficulty":2},
    {"id":"11","name":"朴素贝叶斯","type":"algorithm","difficulty":3},

    {"id":"12","name":"神经网络","type":"model","difficulty":2},
    {"id":"13","name":"CNN","type":"model","difficulty":3},
    {"id":"14","name":"RNN","type":"model","difficulty":3},
    {"id":"15","name":"LSTM","type":"model","difficulty":4},
    {"id":"16","name":"Transformer","type":"model","difficulty":5},
    {"id":"17","name":"注意力机制","type":"mechanism","difficulty":4},

    {"id":"18","name":"反向传播","type":"algorithm","difficulty":3},
    {"id":"19","name":"优化算法","type":"algorithm","difficulty":3},
    {"id":"20","name":"损失函数","type":"concept","difficulty":3},
    {"id":"21","name":"激活函数","type":"concept","difficulty":2},

    {"id":"22","name":"强化学习","type":"paradigm","difficulty":3},
    {"id":"23","name":"特征工程","type":"method","difficulty":3},
    {"id":"24","name":"模型评估","type":"method","difficulty":2},
    {"id":"25","name":"过拟合","type":"problem","difficulty":2},
    {"id":"26","name":"正则化","type":"method","difficulty":3}
  ],

  "relations": [
    {"source":"2","target":"4","type":"contains"},
    {"source":"2","target":"5","type":"contains"},
    {"source":"2","target":"6","type":"contains"},
    {"source":"2","target":"7","type":"contains"},
    {"source":"2","target":"8","type":"contains"},
    {"source":"2","target":"9","type":"contains"},
    {"source":"2","target":"10","type":"contains"},
    {"source":"2","target":"11","type":"contains"},

    {"source":"3","target":"12","type":"contains"},
    {"source":"3","target":"13","type":"contains"},
    {"source":"3","target":"14","type":"contains"},
    {"source":"3","target":"15","type":"contains"},
    {"source":"3","target":"16","type":"contains"},
    {"source":"3","target":"17","type":"contains"},
    {"source":"3","target":"18","type":"contains"},
    {"source":"3","target":"19","type":"contains"},
    {"source":"3","target":"20","type":"contains"},
    {"source":"3","target":"21","type":"contains"},

    {"source":"2","target":"23","type":"used_in"},
    {"source":"2","target":"24","type":"used_in"},
    {"source":"23","target":"4","type":"used_in"},
    {"source":"23","target":"5","type":"used_in"},

    {"source":"4","target":"7","type":"prerequisite"},
    {"source":"4","target":"8","type":"prerequisite"},
    {"source":"4","target":"9","type":"prerequisite"},
    {"source":"4","target":"10","type":"prerequisite"},
    {"source":"4","target":"11","type":"prerequisite"},

    {"source":"5","target":"8","type":"related_to"},
    {"source":"5","target":"10","type":"related_to"},

    {"source":"12","target":"13","type":"prerequisite"},
    {"source":"12","target":"14","type":"prerequisite"},
    {"source":"12","target":"18","type":"prerequisite"},
    {"source":"12","target":"21","type":"used_in"},

    {"source":"13","target":"15","type":"prerequisite"},
    {"source":"14","target":"15","type":"prerequisite"},
    {"source":"14","target":"16","type":"prerequisite"},
    {"source":"15","target":"16","type":"prerequisite"},
    {"source":"16","target":"17","type":"prerequisite"},

    {"source":"18","target":"19","type":"related_to"},
    {"source":"18","target":"20","type":"used_in"},
    {"source":"21","target":"18","type":"used_in"},

    {"source":"19","target":"18","type":"used_in"},
    {"source":"20","target":"24","type":"used_in"},

    {"source":"22","target":"19","type":"used_in"},
    {"source":"22","target":"20","type":"used_in"},

    {"source":"24","target":"25","type":"used_in"},
    {"source":"25","target":"26","type":"related_to"},
    {"source":"26","target":"19","type":"used_in"},
    {"source":"26","target":"18","type":"used_in"},

    {"source":"13","target":"24","type":"used_in"},
    {"source":"16","target":"24","type":"used_in"},
    {"source":"22","target":"24","type":"used_in"},

    {"source":"9","target":"26","type":"used_in"},
    {"source":"8","target":"26","type":"used_in"}
  ]
}