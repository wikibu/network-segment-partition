# `nsp` — Network Segment Partition CLI 设计文档

- 状态：草案（v0.1.0）
- 日期：2026-05-12
- 作者：与用户共同设计

## 1. 概述

`nsp` 是一个用于辅助 VLSM（可变长子网划分）的命令行工具。用户给定一个父网段（IPv4 CIDR）和一组期望的子网前缀长度，工具按规则分配每个子网的 CIDR，并以最大聚合方式列出未使用的剩余地址空间。

### 1.1 目标场景

- 网络规划阶段，把一个大网段切成多个用途各异的子网。
- 输出可直接复制到 Terraform / VPC 控制台 / 文档中使用。
- 支持脚本化（JSON/YAML/CSV/plain 输出）。

### 1.2 非目标（v1 不做）

- IPv6（后续 v2 再加）
- 子网命名以外的元数据（环境、标签、注释等）
- 自动调整请求顺序以外的优化（如按用途分类、对齐策略）
- 性能基准（请求规模 < 1000 时无需关注）
- Hypothesis 属性测试

## 2. 用户体验

### 2.1 CLI 形态

```
nsp -c CIDR -m MASK [MASK ...] [-s] [-o {input,address}]
    [-f {table,json,yaml,csv,plain}] [-h] [-v]
```

### 2.2 选项

| 短 | 长 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|---|
| `-c` | `--cidr` | str | ✅ | — | 父网段，如 `10.10.0.0/16` |
| `-m` | `--mask` | list[str] | ✅ | — | 子网请求列表，支持 `/19` 和 `web=/19` |
| `-s` | `--sort` | flag | ❌ | False | 内部按从大到小重排避免对齐碎片 |
| `-o` | `--order` | choice | ❌ | `input` | 输出行排序：`input` \| `address` |
| `-f` | `--format` | choice | ❌ | `table` | `table` \| `json` \| `yaml` \| `csv` \| `plain` |
| `-v` | `--version` | flag | — | — | 显示版本 |
| `-h` | `--help` | flag | — | — | argparse 自带 |

### 2.3 使用示例

```bash
# 基本示例（用户原始用例）
nsp -c 10.10.0.0/16 -m /19 /20 /21 /21 /19 /20 /21 /21

# 带标签
nsp -c 10.10.0.0/16 -m web=/19 db=/20 cache=/21 backup=/21

# 紧凑分配 + JSON 输出
nsp -c 10.10.0.0/16 -m web=/21 db=/19 cache=/20 -s -f json

# 管道用法（每行一个 CIDR）
nsp -c 10.10.0.0/16 -m /19 /20 -f plain | xargs -I {} echo "subnet: {}"
```

## 3. 分配语义

### 3.1 默认模式（严格按输入顺序）

逐个处理 `-m` 列表中的子网请求，每个请求都从当前游标开始，向上对齐到该前缀长度对应的边界，然后落定。游标推进到该子网结束位置 + 1，继续下一个。

**对齐空隙**：如果输入顺序导致某个子网必须跳过一段地址才能满足 CIDR 对齐（如先 `/21` 后 `/19`），中间留下的空隙会出现在剩余空间列表里。

### 3.2 `--sort` 模式

内部把请求列表按 `prefix_length` 升序（=网段从大到小）稳定排序后再走同一套分配逻辑，避免对齐空隙，地址空间紧凑利用。

输出展示顺序由 `--order` 控制：
- `input`（默认）：按用户输入的原始顺序展示，便于查"label=X 分到哪个 CIDR"。
- `address`：按实际地址升序展示，便于查"最终网络规划图"。

### 3.3 剩余空间

父网段减去所有已分配子网，得到的结果用 `ipaddress.collapse_addresses` 聚合到最大 CIDR 块，按起始地址升序输出。

### 3.4 工作示例

**输入**：`nsp -c 10.10.0.0/16 -m /19 /20 /21 /21 /19 /20 /21 /21`

**分配结果**：

| # | CIDR | SIZE |
|---|---|---|
| 1 | 10.10.0.0/19 | 8192 |
| 2 | 10.10.32.0/20 | 4096 |
| 3 | 10.10.48.0/21 | 2048 |
| 4 | 10.10.56.0/21 | 2048 |
| 5 | 10.10.64.0/19 | 8192 |
| 6 | 10.10.96.0/20 | 4096 |
| 7 | 10.10.112.0/21 | 2048 |
| 8 | 10.10.120.0/21 | 2048 |

**剩余空间**：

| # | CIDR | SIZE |
|---|---|---|
| 1 | 10.10.128.0/17 | 32768 |

（注：原始需求列出 `10.10.128.0/18` 和 `10.10.192.0/18`，但 `collapse_addresses` 会进一步把它们聚合成 `10.10.128.0/17`。本工具按最大聚合输出。）

## 4. 项目结构

```
network-segment-partition/
├── pyproject.toml                # 元数据 + 入口点 nsp = nsp.cli:main
├── README.md
├── src/
│   └── nsp/
│       ├── __init__.py
│       ├── cli.py                # argparse, 入口 main()
│       ├── parser.py             # 解析 -m 参数，"web=/19" → SubnetRequest
│       ├── allocator.py          # 核心算法：分配 + 剩余聚合
│       ├── models.py             # 数据类：SubnetRequest, Allocation, PartitionResult
│       ├── formatters/
│       │   ├── __init__.py       # 工厂函数，按 --format 分发
│       │   ├── table.py
│       │   ├── json_fmt.py
│       │   ├── yaml_fmt.py
│       │   ├── csv_fmt.py
│       │   └── plain.py
│       └── errors.py             # 自定义异常类
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_parser.py
    ├── test_allocator.py
    ├── test_formatters.py
    └── test_cli.py
```

### 4.1 模块职责

- **`cli.py`** ─ argparse、错误码映射、把字符串参数交给 parser/allocator/formatter 串起来。无业务逻辑。
- **`parser.py`** ─ 把 `["web=/19", "/20", ...]` 解析成 `list[SubnetRequest]`。负责标签/前缀格式校验。
- **`allocator.py`** ─ 接收父网段 + `list[SubnetRequest]` + `sort: bool` + `order`，返回 `PartitionResult`。算法核心，唯一一处和 `ipaddress` 库交互。
- **`models.py`** ─ 纯数据类（`@dataclass(frozen=True)`），所有 formatter 消费它。
- **`formatters/*`** ─ 每种输出格式一个文件，输入 `PartitionResult`，输出字符串。互不依赖。
- **`errors.py`** ─ 业务异常类。CLI 层捕获后转退出码 + 友好消息。

### 4.2 数据流

```
CLI args
  → parser.parse_requests() → list[SubnetRequest]
  → allocator.allocate(parent, requests, sort, order) → PartitionResult
  → formatters.get(format).render(result) → str
  → stdout / stderr + exit code
```

## 5. 核心数据模型

```python
# models.py

from dataclasses import dataclass
from ipaddress import IPv4Network

@dataclass(frozen=True)
class SubnetRequest:
    prefix_length: int          # 例如 19、20、21
    label: str | None = None    # None 表示未命名
    order: int = 0              # 在原始 -m 列表中的位置；--sort 时还原输出顺序

@dataclass(frozen=True)
class Allocation:
    request: SubnetRequest
    network: IPv4Network

@dataclass(frozen=True)
class PartitionResult:
    parent: IPv4Network
    allocations: tuple[Allocation, ...]      # 按 order/address 排序后输出
    remaining: tuple[IPv4Network, ...]       # 已 collapse，按起始地址升序
    sorted_internally: bool                  # 是否用了 --sort
```

### 5.1 设计约束

- `tuple` + `frozen=True` 保证不可变。
- `allocations` 顺序由 `--order` 决定；标签和顺序对应关系永远保持（label 跟着 request 走）。
- `remaining` 永远是 collapse 后的最大 CIDR 列表。
- 数据模型只代表"成功的结果"——失败场景由 allocator 直接抛异常，不会构造半成品 `PartitionResult`。

## 6. 分配算法

### 6.1 主流程

```python
def allocate(parent: IPv4Network,
             requests: list[SubnetRequest],
             sort: bool,
             order: Literal["input", "address"]) -> PartitionResult:

    # 1. 容量预检
    requested_total = sum(2 ** (32 - r.prefix_length) for r in requests)
    if requested_total > parent.num_addresses:
        raise CapacityExceededError(short_by=requested_total - parent.num_addresses)

    # 2. 单请求超父网检查
    for r in requests:
        if r.prefix_length < parent.prefixlen:
            raise SubnetTooLargeError(request=r, parent=parent)

    # 3. 决定分配顺序
    work_list = sorted(requests, key=lambda r: r.prefix_length) if sort else requests
    # sorted 稳定，前缀相同的保留原始相对顺序

    # 4. 顺序分配
    cursor = int(parent.network_address)
    parent_end = int(parent.broadcast_address)
    allocations: list[Allocation] = []

    for req in work_list:
        block_size = 2 ** (32 - req.prefix_length)
        aligned = (cursor + block_size - 1) // block_size * block_size

        if aligned + block_size - 1 > parent_end:
            raise CapacityExceededError(
                short_by=aligned + block_size - parent_end - 1,
                hint="alignment gaps consumed available space; try --sort"
            )

        network = IPv4Network((aligned, req.prefix_length))
        allocations.append(Allocation(request=req, network=network))
        cursor = aligned + block_size

    # 5. 还原显示顺序
    if order == "input":
        allocations.sort(key=lambda a: a.request.order)
    else:
        allocations.sort(key=lambda a: int(a.network.network_address))

    # 6. 计算剩余空间
    remaining = _compute_remaining(parent, allocations)

    return PartitionResult(parent, tuple(allocations), tuple(remaining), sorted_internally=sort)
```

### 6.2 剩余空间计算

```python
def _compute_remaining(parent: IPv4Network,
                       allocations: list[Allocation]) -> list[IPv4Network]:
    used = set(a.network for a in allocations)

    remaining = [parent]
    for used_net in sorted(used, key=lambda n: int(n.network_address)):
        new_remaining = []
        for r in remaining:
            if used_net.subnet_of(r):
                new_remaining.extend(r.address_exclude(used_net))
            else:
                new_remaining.append(r)
        remaining = new_remaining

    return list(ipaddress.collapse_addresses(remaining))
```

### 6.3 关键取舍

- **整数运算**：分配循环用 `int` 而非反复构造 `IPv4Network`，性能更稳。
- **稳定排序**：`--sort` 下相同前缀的请求保持原始相对顺序，结果可预测。
- **两次容量检查**：步骤 1 是理论容量（即时反馈），步骤 4 是对齐后实际容量（提示 `--sort`）。
- **标准库优先**：`address_exclude` + `collapse_addresses` 完全靠标准库。

### 6.4 边界场景

- 请求总和等于父网段 → 成功，`remaining` 为空 tuple；输出仍渲染 Remaining 标题下显示 `(none)`，保持结构稳定。
- 单请求 `/32`、`/31` → 允许，用户负责语义。
- 单请求 prefix 等于父网 prefix（如 `parent=/16, mask=/16`）→ 成功填满。
- 单请求 prefix 小于父网 prefix（如 `parent=/16, mask=/15`）→ `SubnetTooLargeError`。

## 7. 输出格式

### 7.1 字段顺序

所有结构化格式（json/yaml/csv）字段顺序统一：`index, cidr, mask, prefix_length, size, range, label`。`label` 在最后，便于人眼快速对照前面的网络信息。表格列序：`#, CIDR, MASK, SIZE, RANGE, LABEL`。

### 7.2 table（默认）

```
Parent: 10.10.0.0/16   (65536 addresses)

Allocated (4):
  #    CIDR                MASK              SIZE    RANGE                         LABEL
  1    10.10.0.0/19        255.255.224.0     8192    10.10.0.0 - 10.10.31.255      web
  2    10.10.32.0/20       255.255.240.0     4096    10.10.32.0 - 10.10.47.255     db
  3    10.10.48.0/21       255.255.248.0     2048    10.10.48.0 - 10.10.55.255     cache
  4    10.10.56.0/21       255.255.248.0     2048    10.10.56.0 - 10.10.63.255     backup

Remaining (2):
  #    CIDR                MASK              SIZE    RANGE
  1    10.10.64.0/18       255.255.192.0     16384   10.10.64.0 - 10.10.127.255
  2    10.10.128.0/17      255.255.128.0     32768   10.10.128.0 - 10.10.255.255
```

实现细节：
- 第一遍扫数据算每列最大宽度（`max(len(header), max(len(row[col])))`）
- 第二遍按宽度 + 4 空格列间距渲染
- 数字列（`#`、`SIZE`）右对齐，文本列左对齐
- LABEL 是最后一列，不加尾部 padding，避免行尾空格
- 未命名行的 LABEL 列显示 `-`
- 当 `allocations` 或 `remaining` 为空时，对应区显示 `(none)`

### 7.3 json

```json
{
  "parent": {
    "cidr": "10.10.0.0/16",
    "size": 65536
  },
  "allocated": [
    {
      "index": 1,
      "cidr": "10.10.0.0/19",
      "mask": "255.255.224.0",
      "prefix_length": 19,
      "size": 8192,
      "range": {"start": "10.10.0.0", "end": "10.10.31.255"},
      "label": "web"
    }
  ],
  "remaining": [
    {
      "index": 1,
      "cidr": "10.10.64.0/18",
      "mask": "255.255.192.0",
      "prefix_length": 18,
      "size": 16384,
      "range": {"start": "10.10.64.0", "end": "10.10.127.255"}
    }
  ],
  "meta": {
    "sorted_internally": false,
    "order": "input",
    "version": "0.1.0"
  }
}
```

- `label` 未命名时为 `null`（不是 `"-"`）
- `remaining` 项无 `label` 字段

### 7.4 yaml

结构与 json 完全一致，仅序列化格式不同。用 `PyYAML` 的 `yaml.safe_dump(..., sort_keys=False)`。

### 7.5 csv

两段输出（空行分隔），每段独立带表头，加 `section` 列区分。

```csv
section,index,cidr,mask,prefix_length,size,range_start,range_end,label
allocated,1,10.10.0.0/19,255.255.224.0,19,8192,10.10.0.0,10.10.31.255,web
allocated,2,10.10.32.0/20,255.255.240.0,20,4096,10.10.32.0,10.10.47.255,db
...
remaining,1,10.10.64.0/18,255.255.192.0,18,16384,10.10.64.0,10.10.127.255,
remaining,2,10.10.128.0/17,255.255.128.0,17,32768,10.10.128.0,10.10.255.255,
```

- `range` 拆成 `range_start` / `range_end` 便于 Excel 列计算
- `label` 在 remaining 行为空字符串

### 7.6 plain

```
10.10.0.0/19
10.10.32.0/20
10.10.48.0/21
10.10.56.0/21
10.10.64.0/18
10.10.128.0/17
```

只输出 CIDR，每行一个，已分配在前剩余在后。不分段、不带标签、不带其他信息。

## 8. 异常处理

### 8.1 异常类

```python
# errors.py

class NSPError(Exception):
    exit_code: int = 1
    def message(self) -> str: ...

class InvalidCIDRError(NSPError):       # 父网段格式错
class InvalidRequestError(NSPError):    # -m 项格式错
class SubnetTooLargeError(NSPError):    # 单请求 >= 父网
class CapacityExceededError(NSPError):  # 总量 / 对齐后超容
```

所有业务错误统一 `exit_code=1`。

### 8.2 错误消息（what + where + how to fix）

```
$ nsp -c 10.10.0.0/24 -m /23
error: subnet /23 is larger than parent 10.10.0.0/24
  → each subnet prefix must be >= 24

$ nsp -c 10.10.0.0/24 -m /25 /25 /25
error: capacity exceeded: requested 384 addresses but parent has 256
  → short by 128 addresses (1 × /25)

$ nsp -c 10.10.0.0/16 -m /21 /19
error: capacity exceeded after alignment: cannot fit /19 at 10.10.8.0
  → alignment gaps consumed 24 addresses
  → try --sort to pack tightly

$ nsp -c 10.10.0.0/16 -m "web!=/19"
error: invalid label 'web!' in '-m' argument
  → labels must match [A-Za-z0-9_-]+

$ nsp -c 10.10.0.0/16 -m /33
error: invalid prefix length /33
  → prefix must be in [0, 32]

$ nsp -c "not-a-cidr"
error: invalid CIDR 'not-a-cidr'
  → expected format: a.b.c.d/N
```

### 8.3 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 业务错误（容量、单请求超父网、CIDR 非法、标签非法等） |
| 2 | argparse 错误（缺参、非法 choice，argparse 自带） |
| 99 | 未捕获异常（兜底，理论上走不到） |

### 8.4 输出去向

| 内容 | 流 |
|---|---|
| 成功结果（table/json/yaml/csv/plain） | stdout |
| 业务错误消息 | stderr |
| argparse 错误（用法、缺参） | stderr |
| 未捕获异常 + traceback | stderr |
| 进度/调试信息 | 无（v1 不输出） |

### 8.5 argparse 与业务校验分工

| 阶段 | 校验项 |
|---|---|
| argparse | `-c`、`-m` 必填；`-f`、`-o` 在 choices 列表中 |
| parser | CIDR 字符串语义；`-m` 项语法（`/N` 或 `label=/N`）；标签字符；前缀范围 [0, 32] |
| allocator | 单请求超父网；容量预检；对齐后实际容量 |

## 9. 测试策略

### 9.1 工具与组织

`pytest`，分层组织：

```
tests/
├── conftest.py              # 共享 fixtures
├── test_models.py
├── test_parser.py
├── test_allocator.py
├── test_formatters.py
└── test_cli.py              # 端到端
```

### 9.2 `test_allocator.py` 必覆盖场景

- 原始用例复现：`10.10.0.0/16` + 8 个请求 → CIDR 列表完全一致
- 严格模式对齐空隙
- `--sort` 模式紧凑
- 请求总和正好 = parent，剩余为空
- 容量预检不通过 → `CapacityExceededError`
- 对齐后实际放不下 → 错误消息含 `try --sort`
- 单请求超父网 → `SubnetTooLargeError`
- 单请求等于父网 → 成功
- `/31`、`/32` 边界
- 标签传递
- 标签重复
- `--sort -o input` vs `--sort -o address` 顺序不同
- 稳定排序

### 9.3 `test_parser.py` 必覆盖

- 合法：`/19`、`web=/19`、`abc_123=/24`、`/0`、`/32`
- 非法：`19`（无斜杠）、`/33`、`/-1`、`web!=/19`、`=/19`、`web=`、`/19/20`、空字符串

### 9.4 `test_formatters.py`

用一个 fixture 构造确定性的 `PartitionResult`，每种格式做"渲染结果 == 预期"的精确比对。JSON/YAML 不比对字符串，而是解析回字典做等价比对。

### 9.5 `test_cli.py` 端到端

用 `subprocess.run(["python", "-m", "nsp.cli", ...])` 启动真实命令，验证：
- 成功路径退出码 0、stdout 有内容、stderr 空
- 业务错误退出码 1、stderr 有 `error:` 前缀、stdout 空
- argparse 错误退出码 2

### 9.6 CI

最小 GitHub Actions workflow：装 Python 3.10+、`pip install -e .[test]`、`pytest`。v1 不强制覆盖率门槛。

## 10. 依赖与运行环境

- **Python**：3.10+（用到 `str | None` 类型语法）
- **运行依赖**：`PyYAML`（仅为 yaml 输出格式）
- **开发依赖**：`pytest`
- **打包**：`pyproject.toml` + `setuptools` 后端，`[project.scripts]` 注册 `nsp` 入口点

## 11. 版本与扩展计划

### 11.1 v0.1.0（本次实现范围）

- 完整覆盖第 2~9 节描述的功能
- IPv4 only

### 11.2 v0.2+ 候选方向（不在本次范围）

- IPv6 支持（数据模型扩展为 `IPv4Network | IPv6Network`）
- 子命令结构（`nsp partition`、`nsp summarize`、`nsp check` 等）
- 从文件读取请求列表（`-m @requests.txt`）
- 自定义剩余空间聚合粒度（如"切成最大 /20"）
- 富终端表格输出（颜色、自动列宽，引入 rich）
