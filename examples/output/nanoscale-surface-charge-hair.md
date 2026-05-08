# Nanoscale Surface Charge Visualization of Human Hair
- 作者：Faduma M. Maddar, David Perry, Rhiannon Brooks, Ashley Page, Patrick R. Unwin
- 期刊/会议：Analytical Chemistry
- 年份：2019
- DOI：10.1021/acs.analchem.8b05977

## 一段话总结
本文首次使用 SICM（扫描离子电导显微镜）结合 FEM（有限元模拟，Finite Element Method）实现了人类头发表面电荷密度的纳米级定量可视化。研究团队采用 hopping mode（跳跃模式）配合 potential-pulse chronoamperometry（电位脉冲计时电流法），在液相环境中对头发表面同步获取形貌和电荷信息。通过对未处理、漂白处理和护发素处理三组头发的对比实验，揭示了化学处理对毛鳞片（cuticle）表面电荷分布的显著影响：漂白使负电荷急剧增大，而护发素中的阳离子表面活性剂能选择性吸附在负电荷最强的区域，使表面电荷从负转正。

## 摘要翻译
我们提出了一种基于扫描离子电导显微镜（SICM）的纳米尺度表面电荷成像方法。利用 SICM 的跳跃扫描模式，在每个像素点施加电位脉冲并记录离子电流响应，再通过有限元模拟（FEM）将归一化电流信号定量转化为表面电荷密度（单位：mC/m²）。该方法在 50 mM KCl 电解液中工作，横向分辨率约 250 nm，可在液相环境中对头发表面进行非接触式成像。我们将其应用于人类头发样品，定量比较了未处理、漂白处理和护发素处理后的表面电荷分布差异，为理解护发产品的作用机制提供了前所未有的纳米级视角。

## 框架
```
问题定义（传统方法无法纳米级定量成像头发表面电荷）
    │
    ▼
方法设计（SICM hopping mode + 电位脉冲 + FEM 定量转化）
    │
    ▼
方法验证（已知电荷密度的标准样品校准）
    │
    ▼
应用实验（三组对比：未处理 / 漂白 / 护发素）
    │
    ▼
定量分析（电荷密度统计 + 形貌-电荷关联）
    │
    ▼
机制讨论（漂白破坏 18-MEA 脂质层 → 暴露负电荷基团；
          阳离子表面活性剂优先吸附在高负电荷区域）
```

## 研究问题
头发表面电荷是决定护发产品效果的关键物理化学参数——阳离子护发素之所以能"修复"受损头发，正是因为它被负电荷吸引到受损区域。但传统方法存在明显局限：

- **Zeta 电位测量**：只能给出整根头发的平均电荷值，无法看到纳米尺度的空间分布
- **KPFM（开尔文探针力显微镜）**：需要在空气中测量，湿度和污染会严重干扰结果，而且只能给出相对值，不是定量的电荷密度

本文要解决的核心问题是：**如何在接近生理条件的液相环境中，对头发表面电荷进行纳米级的定量成像？**

## 方法
SICM hopping mode + potential-pulse chronoamperometry 联合测量方案：

1. **探针制备**：用激光拉制器将硼硅玻璃毛细管（外径 1.2 mm，内径 0.69 mm）拉制成纳米移液管，孔径约 220 nm
2. **扫描方式**：hopping mode——探针在每个像素点垂直接近表面，到达设定距离后退回，再移动到下一个像素。避免了接触模式中探针刮伤样品的问题
3. **距离控制**：监测离子电流，当电流下降 3%（对应探针-表面距离约 30 nm）时停止接近
4. **电荷测量**：在每个像素点，将探针电位从 +50 mV 切换到 -400 mV，持续 50 ms，记录瞬态电流响应。表面电荷会影响探针附近的离子分布，从而改变电流响应的幅度
5. **定量转化**：用 COMSOL Multiphysics 建立 FEM 模型，模拟不同表面电荷密度下的电流响应曲线，建立"归一化电流 → 电荷密度"的查找表（lookup table）

### 关键实验参数
- Probe aperture：~220 nm
- Electrolyte：50 mM KCl
- Scan mode：Hopping mode
- Setpoint：3% current drop (~30 nm tip-surface distance)
- Potential pulse：+50 mV → -400 mV, 50 ms duration
- Pixel spacing：250 nm (lateral)
- Retract speed：20 um/s
- Sample：25-year-old Caucasian male light brown hair

## 关键结果
1. **未处理头发（clean hair）**：表面电荷密度较均匀，平均约 -15 mC/m²（pH 6.8 条件下），少数区域可达 -35 mC/m²。负电荷主要集中在毛鳞片边缘附近，这与边缘处 18-MEA 脂质层较薄、氨基酸基团暴露更多的结构特征一致
2. **漂白处理后（bleached hair）**：表面电荷急剧增大为强负值，部分区域可达 -100 mC/m²，分布极不均匀。形貌也明显变粗糙——毛鳞片台阶高度从约 0.8 um 增至约 2.5 um。这是因为漂白剂（双氧水）氧化破坏了 18-MEA 脂质保护层，暴露出大量带负电的 cysteic acid（磺基丙氨酸）残基
3. **护发素处理后（conditioned hair）**：表面出现正电荷区域，整体电荷从负转正约 +5 mC/m²，表面变得更平滑。关键发现：阳离子表面活性剂优先吸附在负电荷最强的区域——这从分子层面解释了护发素"哪里受损修哪里"的作用机制

## 创新点
- 首次实现头发表面电荷的纳米级定量成像（之前只有平均 zeta 电位或 KPFM 半定量数据）
- SICM 在液相中工作，避免了 KPFM 在空气中测量的湿度和污染干扰问题
- 同步获取形貌 + 电荷双通道数据，可直接关联毛鳞片微观结构与电荷分布
- 通过 FEM 模拟建立了从电流信号到表面电荷密度的定量转化方法，基于 Gouy-Chapman 双电层模型
- 可在同一根头发的不同位置成像（根部 vs 末端），展示沿发干方向的老化/损伤梯度

## 局限性
- 只测了一位供体的头发（25 岁白种男性），样本代表性有限，不同种族、年龄、发色的头发可能有不同的电荷特征
- FEM 模型假设平面基底，而头发曲率半径（50-100 um）虽然远大于探针尺寸（220 nm），但在毛鳞片边缘等曲率较大的区域可能引入误差
- 扫描区域较小（约 10x10 um），难以反映整根头发的统计分布
- 护发素成分未详细公开（使用的是商业产品），无法精确分析哪种阳离子成分起主要作用
- 未系统讨论电解液浓度对电荷测量的影响（只用了 50 mM KCl 一个浓度）

## 值得追踪的参考文献
- Perry, D. et al., "Surface Charge Visualization at Viable Living Cells", JACS 2016 — 该课题组首次实现 SICM 形貌+电荷同步测量的方法论文
- Kang, M. et al., "High-Speed Functional Mapping of Single Cells", ACS Nano 2017 — hopping mode 的速度和精度提升
- Page, A. et al., "Quantitative Visualization of Molecular Delivery and Uptake at Living Cells", Anal. Chem. 2016 — potential-pulse chronoamperometry 方法的详细描述
- Takahashi, Y. et al. — SICM 用于活细胞等软样品成像的系列工作
- Robbins, C. R., "Chemical and Physical Behavior of Human Hair", 5th ed. — 头发化学物理性质的经典教材
- Negri, A. P. et al., Textile Research Journal 1993 — 头发表面 zeta 电位的早期测量工作
