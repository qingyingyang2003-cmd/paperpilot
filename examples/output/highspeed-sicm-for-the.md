# High-Speed SICM for the Visualization of Nanoscale Dynamic Structural Changes in Hippocampal Neurons
- 作者：Yasufumi Takahashi, Yuanshu Zhou, Takafumi Miyamoto, Hiroki Higashi, Noritaka Nakamichi, Yuka Takeda, Yukio Kato, Yuri Korchev, and Takeshi Fukuma
- 期刊/会议：Analytical Chemistry
- 年份：2020
- DOI：10.1021/acs.analchem.9b04775
## 一段话总结
本文报道了一种新型高速SICM（扫描离子电导显微镜）扫描方法——AR（automation region of interest，自动感兴趣区域）模式SICM，专门用于对海马神经元纳米尺度动态结构变化进行无标记成像。研究团队通过开发一种基于前一帧图像预测细胞位置、自动选择下一帧扫描区域的算法，将扫描时间缩短了约一半。结合自制高谐振频率Z轴压电扫描器（30 kHz），该系统成功实现了对树突棘（dendritic spine）和突触小体（synaptic bouton）体积变化、线粒体货物运输（cargo transport）、生长锥（growth cone）细胞骨架重排，以及突触形成过程的实时可视化。此外，该技术还首次在无荧光标记的条件下直接观测到了质膜前体囊泡（plasmalemmal precursor vesicles，ppvs）的转运过程，展示了SICM在神经生物学研究中的独特优势。

## 摘要翻译
细胞骨架的动态重组以及树突棘（dendritic spine）、货物运输（cargo transport）和突触形成（synapse formation）所代表的结构变化与记忆密切相关。然而，由于光学显微镜的衍射极限，纳米尺度形貌的可视化面临极大挑战。扫描离子电导显微镜（SICM）是一种在无需标记的条件下可视化细胞表面纳米尺度形貌变化的有效工具，但其时间分辨率是活细胞延时成像的关键瓶颈。本研究开发了一种新型扫描方法——自动感兴趣区域（AR）模式SICM，通过预测细胞位置来自动选择下一帧成像区域，从而将延时成像的扫描时间缩短了一半。利用该方法获得的延时图像不仅提供了树突棘和突触小体体积变化及神经网络形成过程的新型纳米尺度结构信息，还提供了与记忆密切相关的定量数据。此外，尚未建立荧光标记方法的质膜前体囊泡（ppvs）的转运过程，以及生长锥处细胞骨架的重排，也得到了直接可视化。

## 框架
研究框架遵循"问题识别 → 技术开发 → 系统验证 → 生物学应用"的逻辑主线：

**1. 问题识别**
- 神经元纳米尺度动态结构（树突棘、突触小体、生长锥）与记忆功能密切相关
- 荧光显微镜受衍射极限制约，且荧光蛋白标记可能干扰膜运输过程
- 传统SICM时间分辨率不足，无法满足活细胞延时成像需求
- 神经元具有高纵横比结构（细树突 + 大胞体），给扫描带来额外挑战

**2. 技术开发**
- 开发AR模式扫描算法：利用前一帧图像预测细胞位置，自动划定下一帧扫描区域，跳过无细胞区域
- 开发高谐振频率Z轴压电扫描器（30 kHz），减少Z轴过冲（overshoot），实现非接触成像
- 三参数优化（平面拟合、高度阈值、图像膨胀）确保细胞区域识别准确性

**3. 系统性能验证**
- 定量比较AR模式与传统扫描模式的扫描时间（98 s vs 239 s）
- 对比高/低谐振频率压电器对神经元损伤的影响（bleb形成实验）

**4. 生物学应用验证**
- 货物运输（线粒体）可视化
- 树突棘与突触小体体积变化定量分析
- 生长锥细胞骨架动态重排观测
- ppvs转运的无标记可视化
- 突触形成过程的实时追踪

## 研究问题
**核心科学问题：**
如何在不使用荧光标记的前提下，以足够高的时间分辨率对活体海马神经元的纳米尺度动态结构变化进行实时可视化？

**具体子问题：**
1. 如何提升SICM的扫描速度，使其满足神经元动态过程（树突棘变化、货物运输、突触形成）的时间尺度要求？
2. 如何在保证非接触成像的前提下，避免Z轴压电器过冲对脆弱神经元结构造成损伤？
3. 对于尚无可靠荧光标记的生物过程（如ppvs转运），SICM能否提供独立的形貌学证据？

**研究空白：**
- 传统SICM扫描速度慢，对神经元这类具有高纵横比结构的样品尤为突出
- 荧光显微镜虽能实现动态成像，但标记本身可能干扰膜运输，且无法提供真实的高度/体积定量信息
- 快速原子力显微镜（fast-scan AFM）虽可用于神经元成像，但对具有微米级陡峭侧壁的神经突起追踪仍有困难
- ppvs等细胞器缺乏特异性生化标记，其转运过程的直接观测存在技术空白

## 方法
**SICM系统构建：**
- 探针：硼硅酸盐玻璃纳米移液管（nanopipette），孔径内半径约50 nm，由CO₂激光拉制仪（Sutter P-2000）制备
- 电极：Ag/AgCl电极，施加电压 −0.2 V，产生离子电流作为反馈信号
- 电流放大器：自制1 GΩ反馈电阻电流放大器
- Z轴扫描器：自制高谐振频率压电扫描器，电容0.75 μF，谐振频率30 kHz
- 控制软件：LabVIEW 2014编写，FPGA（NI USB-7856 OEM）实时控制
- 整体平台：搭建于倒置光学显微镜（Nikon ECLIPSE Ti-S）上，置于防振台

**AR模式算法：**
1. 先采集两帧连续图像，确定三个参数：平面拟合（消除样品倾斜）、高度阈值（通常250 nm，区分细胞与基底）、图像膨胀（dilation，预测细胞形状变化）
2. 基于前一帧图像预测细胞位置，自动划定下一帧扫描区域，跳过无细胞像素
3. 扫描区域分为三类：含细胞区（红）、无细胞扫描区（蓝）、非扫描区（绿）

**Hopping模式参数：**
- 跳跃幅度：1–3 μm
- 横向移动后等待时间：1 ms（用于测量参考电流IREF）
- 探针下落/回缩速度：150–320 / 1200 nm/ms（快速Z轴）；50 / 900 nm/ms（慢速Z轴，对照）
- 设定点：99.3%–99.7% × IREF

**海马神经元培养：**
- 取材：ICR小鼠胚胎第15天海马，0.25%胰蛋白酶消化后机械解离
- 铺板密度：1.5 × 10⁴ cells/cm²，聚L-赖氨酸包被盖玻片
- 培养基：B-27 Electrophysiology Kit，含青霉素/链霉素/谷氨酰胺，初期加谷氨酸（25 μM）
- 成像时间点：1、2、4、7、10、14、16、17 DIV（days in vitro，体外培养天数）

**多模态联合成像：**
- SICM与共聚焦显微镜同步成像，用MitoTracker Green FM标记线粒体，验证货物运输分子身份

**数据分析：**
- 体积变化通过截面图（cross-section）定量分析
- 货物运输速度通过延时图像中位移/时间计算
- 扫描效率通过像素数统计定量评估

### 关键实验参数
- Probe aperture inner radius：50 nm
- Applied voltage：−0.2 V
- Current amplifier feedback resistance：1 GΩ
- Z-piezo capacitance (fast)：0.75 μF
- Z-piezo resonance frequency (fast)：30 kHz
- Z-piezo resonance frequency (slow, control)：6.2 kHz
- Hopping amplitude：1–3 μm
- Lateral movement waiting time：1 ms
- Probe falling speed (fast Z)：240 nm/ms
- Probe withdrawing speed (fast Z)：1200 nm/ms
- Probe falling speed (slow Z)：50 nm/ms
- Probe withdrawing speed (slow Z)：900 nm/ms
- Set point：99.3%–99.7% of IREF
- Height threshold (AR mode)：250 nm
- Current/distance signal sampling rate：10 kHz
- Scan size (AR mode, dendrite)：15 × 15 μm²
- Scan size (high-magnification neurite)：5 × 5 μm²
- Scan size (growth cone)：18–30 × 18–30 μm²
- Pixel size (high-magnification)：64 × 64
- AR mode scanning time：98 s/frame
- Conventional scanning time：239 s/frame
- Cell plating density：1.5 × 10⁴ cells/cm²
- Trypsin concentration：0.25%
- Poly-L-lysine coating：7.5 μg/mL
- Glutamate (initial culture)：25 μM
- CO₂ incubator：5% CO₂, 37 °C

## 关键结果
1. **AR模式显著提升扫描速度：** AR模式扫描时间为98 s/帧，传统模式为239 s/帧，扫描时间缩短约59%（接近减半）。在典型扫描区域中，无细胞扫描像素占比29.3%，非扫描区像素占比约52%，说明AR模式有效跳过了大量无效扫描区域。

2. **微管束的无标记直接可视化：** 在树突形貌图像中直接观测到微管束（microtubule bundle）的致密排列结构，其形态和尺寸与文献报道一致，无需任何标记。

3. **货物运输的实时追踪：** 在树突上观测到沿微管束的货物运输（推测为线粒体介导），运输速度约为0.011 μm/s，低于文献报道的典型值（0.91 ± 0.26 μm/s），作者认为这与所捕获的线粒体处于低运动状态有关。SICM与共聚焦显微镜联合成像证实了货物的线粒体属性。

4. **树突棘与突触小体体积变化定量：** 在14 DIV神经元中观测到树突棘样突起（高度700 nm，宽度500 nm）。在17 DIV神经元中，突触小体高度从3 μm自发降至1.5 μm，其动态时间尺度与超分辨显微镜文献报道一致。

5. **神经网络形成过程可视化：** 在突触小体或静脉曲张（varicosity）周围观测到肌动蛋白丝（actin filament）的动态重组和肌动蛋白波状传播（actin wave-like propagation），随后发生神经网络连接形成。

6. **高谐振频率Z轴压电器的必要性验证：** 使用低谐振频率（6.2 kHz）Z轴压电器时，过冲导致纳米移液管与样品接触，在神经突起上诱发了囊泡（bleb）形成；而高谐振频率（30 kHz）压电器将过冲时间从0.6 ms缩短至0.2 ms，有效避免了样品损伤。

7. **生长锥细胞骨架动态重排：** 观测到P域（peripheral domain）的自发扩张（135 s内恢复原状）、片状伪足（lamellipodia）的同步收缩、肌动蛋白束波状重组，以及ppvs的货物运输，均无需荧光标记。

8. **突触形成过程的实时观测：** 在17 DIV神经元中观测到片状结构从树突中部伸出并延伸至邻近树突，随后形成丝状伪足（filopodia）并与最近的神经突起粘附，形成突触连接。该过程与丝状伪足模型（filopodial model）吻合。

## 创新点
**1. AR模式扫描算法（核心创新）：**
这是本文最主要的技术贡献。通过利用前一帧图像预测细胞位置并自动划定扫描区域，AR模式将扫描时间缩短约一半，且无需人工干预。与Novak等人的预扫描变像素方法不同，AR模式通过图像膨胀（dilation）参数预测细胞形状变化，更适合追踪动态变化的神经元结构。

**2. 高谐振频率Z轴压电扫描器：**
自制30 kHz谐振频率Z轴压电扫描器（电容0.75 μF），相比常规低频压电器，显著减少了hopping模式中的Z轴过冲，实现了对脆弱神经元结构（树突棘、生长锥）的真正非接触成像。这解决了高速SICM中硬件层面的关键瓶颈。

**3. ppvs转运的无标记直接可视化：**
质膜前体囊泡（ppvs）目前尚无可靠的荧光标记方法，传统研究依赖脉冲标记策略间接推断。本文首次通过SICM直接观测到ppvs在生长锥处的转运过程，为这一重要生物学现象提供了形貌学直接证据。

**4. 多种神经元动态过程的综合无标记成像平台：**
将AR模式算法、高速Z轴扫描器与SICM-共聚焦联合成像整合为一个完整平台，在单一系统中实现了货物运输、树突棘/突触小体体积变化、细胞骨架重排和突触形成的定量可视化，覆盖了从分子运输到网络形成的多个时空尺度。

**5. 与前人工作的区别：**
- 相比Ida等人（2017）的优化hopping幅度算法，AR模式避免了与浮动结构（如树突棘）碰撞的风险
- 相比fast-scan AFM（Shibata等，2015），SICM对具有微米级陡峭侧壁的神经突起追踪更具优势
- 相比双Z轴压电系统（Shevchuk等，2012），本文方案在单一高频压电器上实现了类似的非接触效果

## 局限性
**1. 时间分辨率仍有不足：**
即使经过AR模式优化，每帧扫描时间仍在68–98 s量级，对于快速货物运输（典型线粒体运输速度0.91 μm/s）仍然太慢。文中观测到的线粒体运输速度（0.011 μm/s）远低于文献值，说明系统只能捕获低运动状态的货物，快速动态过程仍然难以追踪。

**2. AR模式的局限性：**
当细胞形状变化超出前一帧预测范围，或有新结构从成像区域外进入视野时，AR模式可能无法完整捕获细胞形貌。作者也承认需要比较多帧连续图像并手动调整参数来应对这种情况，降低了自动化程度。

**3. 成像区域受限：**
SICM的扫描范围相对有限（本文最大30 × 30 μm²），对于需要追踪大范围神经网络形成或长距离货物运输的研究场景，覆盖面积不足。

**4. 分子身份鉴定依赖联合成像：**
SICM本身只能提供形貌信息，无法直接鉴定观测到的结构的分子身份。对于线粒体的确认需要借助共聚焦显微镜联合成像，而ppvs的身份认定仍主要基于形态学推断，缺乏分子层面的直接验证。

**5. 样品制备与成像条件的限制：**
神经元培养在盖玻片上，成像在开放溶液环境中进行，与体内生理环境存在差异。此外，长时间延时成像过程中维持神经元活性和稳定性是一个潜在挑战，文中未详细讨论成像期间的细胞活力评估。

**6. 定量分析的局限：**
体积变化主要通过截面高度变化来估算，未考虑侧面形貌的完整三维重建，可能低估实际体积变化。

**7. 未解决的生物学问题：**
虽然观测到了ppvs转运和突触形成过程，但这些过程的分子调控机制、与神经活动的因果关系，以及与记忆形成的直接联系，仍需进一步研究。


## 值得追踪的参考文献
- (1) Hansma, P. K.; Drake, B.; Marti, O.; Gould, S. A. C.; Prater, C. B. Science 1989, 243, 641−643.
- 【SICM技术的奠基性论文，首次报道扫描离子电导显微镜原理】
- (2) Novak, P.; Li, C.; Shevchuk, A. I.; Stepanyan, R.; Caldwell, M.; Hughes, S.; Smart, T. G.; Gorelik, J.; Ostanin, V. P.; Lab, M. J.; Moss, G. W. J.; Frolenkov, G. I.; Klenerman, D.; Korchev, Y. E. Nat. Methods 2009, 6, 279−281.
- 【Hopping模式SICM的关键发展论文，提出变像素预扫描方法，是本文AR模式的直接前驱工作】
- (3) Shevchuk, A. I.; Novak, P.; Taylor, M.; Diakonov, I. A.; Ziyadeh-Isleem, A.; Bitoun, M.; Guicheney, P.; Lab, M. J.; Gorelik, J.; Merrifield, C. J.; Klenerman, D.; Korchev, Y. E. J. Cell Biol. 2012, 197, 499−508.
- 【双Z轴压电系统的开发，解决hopping模式过冲问题，与本文高频Z轴压电器方案直接相关】
- (4) Ida, H.; Takahashi, Y.; Kumatani, A.; Shiku, H.; Matsue, T. Anal. Chem. 2017, 89, 6015−6020.
- 【本课题组前期工作，开发了优化hopping幅度的扫描算法，是AR模式的直接前驱】
- (5) Zhou, Y. S.; Saito, M.; Miyamoto, T.; Novak, P.; Shevchuk, A. I.; Korchev, Y. E.; Fukuma, T.; Takahashi, Y. Anal. Chem. 2018, 90, 2891−2895.
- 【本课题组关于SICM非接触成像准则的前期工作，为本文高速非接触成像提供了理论基础】
- (6) Shibata, M.; Uchihashi, T.; Ando, T.; Yasuda, R. Sci. Rep. 2015, 5, 08724.
- 【快速原子力显微镜（fast-scan AFM）用于海马神经元成像的代表性工作，是本文的主要竞争技术参照】
- (7) Kasai, H.; Fukuda, M.; Watanabe, S.; Hayashi-Takagi, A.; Noguchi, J. Trends Neurosci. 2010, 33, 121−129.
- 【树突棘结构变化与记忆关系的重要综述，为本文的生物学研究背景提供核心依据】
- (8) Pfenninger, K. H. Nat. Rev. Neurosci. 2009, 10, 251−261.
- 【ppvs与神经元质膜扩张关系的重要综述，为本文ppvs可视化研究提供生物学背景】
