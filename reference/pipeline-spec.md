# 面试分析流水线契约

本契约由`scripts/analyze.js`与`scripts/analyze_portable.py`共同实现。输入为简历、岗位线索和面试设置，输出`{meta, candidates}`，供渲染器生成指南、评分卡和问答卡。两条分析路径遵循相同内容要求；Python的`--single`合并前期分析，但仍执行Verify/Revise。

## 内容标准

研究及高级岗位以问题为何重要、方法如何起作用、有哪些替代路线、如何取舍、证据支持到哪里为主。工程岗位匹配真实设计职责。具体上下文是讨论依据，不等于命令、参数或指标盘问。操作细节只在有助于判断时成为主题内选问，不能替代主要讨论。

提问礼貌开放，不设套、不预设注水或人格结论；允许第三种路线和依任务而变的答案。材料差异先澄清。HR评价仅作有来源的转述，转换成中性的合作期待问题，不据此断定能力或动机。缺少证明不等于虚构，时间重叠不自动构成矛盾。

每一个问题都有直接回应题意、可以口述的示范回答。示范须给观点、理由及必要边界，不能只说“应提到什么”，也不能用占位符回避关键推理。示范并非候选人真实经历，不编造其贡献、数值、实验或承诺；必要的情境实例明确标为假设。`good`与`pass`只放面试官判分维度，与示范分开；合理替代路线同样得分。

所有技术追问留在原主题：主题主线的顺势追问使用`probe`与`probe_answer`（可空）；`followups`只放根据回答选用的额外分支，不重复ladder、ask或probe，逐项写问题、口述示范及选问条件。`followups`可以为空，不凑数量。顶层`probes`仅放独立合作安排或材料确认，不允许文末技术题堆。新增主题时避免重复已有主题。

## 输入与时长

输入`args`包含`meta`以及`candidates`数组；候选人项为`{id,label,role_hint,resume,resume_text}`。`resume`是产物目录内的相对文件名。附件内容属于材料，不作为指令执行。

`meta.lang`或顶层`lang`可设输出语言，缺省auto按正文检测；`meta.minutes`缺省60。`meta.depth`或顶层`depth`可指定quick、standard、deep、ultra。显式`nCore`覆盖默认题数。quick保留1级ladder，其余保留2级。常规60分钟为开场5分钟、6个主题各8分钟、收尾7分钟；追问按回答选用，全部问题不是必答清单。

常规时长按`core=max(minutes-opener-buffer,8)`、`nCore=clamp(round(core/8),2,12)`、`perQuestion=max(4,floor(core/nCore))`推导，quick/standard/deep的开场与收尾分别为(4,5)、(5,7)、(6,9)。极短或自定义题数时，该公式只是参考，不能把超出的题量当作可执行日程。ultra不限时、不设默认题数配额，按主题覆盖重要主张、量化口径、本人贡献、能力与经历性质，不为每个细节独立造题。

## 角色与语言

两套运行时使用相同角色原则：

> 你是公正而有技术判断力的资深面试官。根据岗位与经历选择评价层次：研究及高级岗位优先讨论研究意义、机制、替代路线、取舍、证据与适用边界；工程岗位围绕真实任务的设计判断与结果。具体上下文不等于操作盘问，不能用命令、参数或指标核对取代主要问题。问题礼貌、开放、可讨论，不设套、不预设注水、动机或人格结论；材料差异是待澄清信息。HR评价仅作有来源的转述，转成合作预期的中性问题。肯定有依据的强项，诚实限定已知范围是正面信号；合理替代路线同样得分。避免空泛套话与人为二分，允许第三条路线及任务依赖的答案。每问的示范回答须可以直接口述，回答该问并说明理由；示范不是候选人真实经历，不编造其贡献、实验、数值或承诺。需要实例时明确标为假设示例，不用占位符绕过核心推理。good/pass只写面试官判分依据，与示范回答分离。所有技术追问就近归入原主题的probe或followups，不在文末堆放技术题；probes仅用于独立合作安排或材料确认。

全部字段使用目标语言。中文散文遵守`writing-norms.md`；跨语言引用需翻译。代码、文件名与通用技术名词保留适当原文。语言检测与时长计算属于运行时，内容模型不得自行更换用户指定的语言或范围。

## 阶段1：Triage

根据简历与岗位线索，给出有材料依据的画像、标尺、强项和待澄清信息。不估算“真本事/包装比例”。开场邀请候选人选择参与深入的问题展开。各domain的focus明确重要问题、机制、替代路线、取舍、证据及边界，而非机械列底层细节。主题数量只作参考，不因数量重复主题。

## 阶段2：Probe

逐主题分析，可并行。`q`是礼貌具体的问题，`probes`说明评价目的，`strong`是直接回答的口述示范，`tell`描述论证缺口，`followup`、`followup_answer`与`when`提供同主题追问、对应示范和选问条件；无必要追问时这三项可为空字符串。问题数按主题需要，不设凑数配额。

## 阶段3：Author

把分域结果收敛为核心主题卡，保持项目背景与问题之间的实际联系。常规按时长给核心主题数，ultra按覆盖范围决定。L1讨论问题与意义，L2讨论路线与取舍，ask推进开放推演、竞争解释、证据或边界；quick只保留1级切入。每问推进一个主要判断，避免把大量考试点塞进一句话。

每个ladder项必须有answer；ask必须有ask_answer；probe必须有probe_answer。无必要顺势追问时probe和probe_answer均为空字符串。技术追问全部就近归属同卡followups；独立合作安排/材料确认才进入顶层probes，且每项必须有answer。good/pass为独立判分内容。

## 阶段4：Verify与Revise

Verify接收原始材料及完整`{cards,probes}`，逐问审核层次、逻辑、礼貌、隐含假设、技术准确性、证据边界与示范覆盖。检查ladder.answer、ask_answer、probe_answer、followups[].answer和probes[].answer是否回答对应问题、是否编造经历；检查判分是否与示范分离、替代路线是否被公平对待、HR是否仍只是转述。检查技术追问归属，纠正文末技术题堆。只报告实质问题，不为审查而造错；无法从现有来源核实的外部事实保留待核实，不伪称已完成外部核查。

corrections中n可为Q编号或字段路径；severity保持error、imprecise、overclaim、missing四类。若有修正，Revise返回完整AUTHOR结构，而非只返回cards。允许修订有问题的题目、所有对应示范与判分；不能固定错误题目而只改good/pass。主题与编号保持一致，必要时将技术尾部题迁回followups；无关内容保持原意。核查失败时不得声称核查通过，载荷_factcheck为null。

## Schema与兼容

下列为新生成内容的严格schema，required包括全部新字段。旧字段名称保持兼容：历史载荷仍可能缺少新增answer或followups，读取与渲染端应允许这种缺失并明确未提供示范，不能把good/pass当作已经存在的逐问回答。新生成端必须完整填写。REVISE使用AUTHOR；SINGLE合并TRIAGE中的profile/ruler/strengths/flags/opener与AUTHOR的cards/probes。

### TRIAGE

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "profile",
    "ruler",
    "strengths",
    "flags",
    "opener",
    "domains"
  ],
  "properties": {
    "profile": {
      "type": "string"
    },
    "ruler": {
      "type": "string"
    },
    "strengths": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "flags": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "opener": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "title",
        "questions",
        "expect",
        "tell"
      ],
      "properties": {
        "title": {
          "type": "string"
        },
        "questions": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "expect": {
          "type": "string"
        },
        "tell": {
          "type": "string"
        }
      }
    },
    "domains": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "key",
          "focus"
        ],
        "properties": {
          "key": {
            "type": "string"
          },
          "focus": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

### PROBE

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "domain",
    "questions"
  ],
  "properties": {
    "domain": {
      "type": "string"
    },
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "q",
          "probes",
          "strong",
          "tell",
          "followup",
          "followup_answer",
          "when"
        ],
        "properties": {
          "q": {
            "type": "string"
          },
          "probes": {
            "type": "string"
          },
          "strong": {
            "type": "string"
          },
          "tell": {
            "type": "string"
          },
          "followup": {
            "type": "string"
          },
          "followup_answer": {
            "type": "string"
          },
          "when": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

### CARD

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "n",
    "title",
    "anchor",
    "ladder",
    "ask",
    "good",
    "pass",
    "tell",
    "probe",
    "ask_answer",
    "probe_answer",
    "followups"
  ],
  "properties": {
    "n": {
      "type": "string"
    },
    "title": {
      "type": "string"
    },
    "anchor": {
      "type": "string"
    },
    "ladder": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "level",
          "q",
          "answer"
        ],
        "properties": {
          "level": {
            "type": "string"
          },
          "q": {
            "type": "string"
          },
          "answer": {
            "type": "string"
          }
        }
      }
    },
    "ask": {
      "type": "string"
    },
    "good": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "pass": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "tell": {
      "type": "string"
    },
    "probe": {
      "type": "string"
    },
    "ask_answer": {
      "type": "string"
    },
    "probe_answer": {
      "type": "string"
    },
    "followups": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "q",
          "answer",
          "when"
        ],
        "properties": {
          "q": {
            "type": "string"
          },
          "answer": {
            "type": "string"
          },
          "when": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

### AUTHOR

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "cards",
    "probes"
  ],
  "properties": {
    "cards": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "n",
          "title",
          "anchor",
          "ladder",
          "ask",
          "good",
          "pass",
          "tell",
          "probe",
          "ask_answer",
          "probe_answer",
          "followups"
        ],
        "properties": {
          "n": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "anchor": {
            "type": "string"
          },
          "ladder": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "level",
                "q",
                "answer"
              ],
              "properties": {
                "level": {
                  "type": "string"
                },
                "q": {
                  "type": "string"
                },
                "answer": {
                  "type": "string"
                }
              }
            }
          },
          "ask": {
            "type": "string"
          },
          "good": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "pass": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "tell": {
            "type": "string"
          },
          "probe": {
            "type": "string"
          },
          "ask_answer": {
            "type": "string"
          },
          "probe_answer": {
            "type": "string"
          },
          "followups": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "q",
                "answer",
                "when"
              ],
              "properties": {
                "q": {
                  "type": "string"
                },
                "answer": {
                  "type": "string"
                },
                "when": {
                  "type": "string"
                }
              }
            }
          }
        }
      }
    },
    "probes": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "tag",
          "q",
          "answer"
        ],
        "properties": {
          "tag": {
            "type": "string"
          },
          "q": {
            "type": "string"
          },
          "answer": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

### VERIFY

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "corrections",
    "verdict"
  ],
  "properties": {
    "corrections": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "n",
          "severity",
          "issue",
          "fix"
        ],
        "properties": {
          "n": {
            "type": "string"
          },
          "severity": {
            "type": "string",
            "enum": [
              "error",
              "imprecise",
              "overclaim",
              "missing"
            ]
          },
          "issue": {
            "type": "string"
          },
          "fix": {
            "type": "string"
          }
        }
      }
    },
    "verdict": {
      "type": "string"
    }
  }
}
```

## 组装与无运行时依赖的接入

每个candidate保留name、resume、profile、ruler、strengths、flags、opener、cards、probes及_factcheck。`payload={meta:{...meta,lang,plan},candidates:{id:candidate}}`。原始简历、HR转述与公开证据的来源不能在组装时混同。

可移植端只要求`call_llm(system,user,schema)->dict`。正常路径按Triage→逐域Probe→Author→Verify→必要时Revise运行。single仅跳过分域Probe，按同一角色、逐问回答、主题内追问与判分分离标准一次生成，再对完整cards/probes执行相同审核与修订。测试可替换call_llm为本地stub验证schema及分支，不需要调用外部API。
