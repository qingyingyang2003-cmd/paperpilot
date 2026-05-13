# High-Speed SICM for the Visualization of Nanoscale Dynamic Structural Changes in Hippocampal Neurons
- 作者：Yasufumi Takahashi, Yuanshu Zhou, Takafumi Miyamoto, Hiroki Higashi, Noritaka Nakamichi, Yuka Takeda, Yukio Kato, Yuri Korchev, and Takeshi Fukuma
- 期刊/会议：Analytical Chemistry
- 年份：2020
- DOI：10.1021/acs.analchem.9b04775
## 一段话总结
本文报道了一种新型高速SICM（扫描离子电导显微镜）扫描方法——AR（automation region of interest，自动感兴趣区域）模式SICM，专门用于对海马神经元纳米尺度动态结构变化进行无标记成像。该方法通过预测细胞位置来自动选择下一帧的扫描区域，将扫描时间缩短了约一半（从239秒降至98秒）。结合自主研发的高谐振频率Z轴压电扫描器（30 kHz），研究团队成功实现了对树突棘（dendritic spine）和突触小体（synaptic bouton）体积变化、质膜前体囊泡（plasmalemmal precursor vesicles, ppvs）的货物运输、生长锥（growth cone）细胞骨架重排以及突触形成过程的直接可视化，为理解记忆相关神经元结构动态提供了全新的定量信息。

## 摘要翻译
细胞骨架的动态重组以及以树突棘、货物运输和突触形成为代表的结构变化与记忆密切相关。然而，由于光学显微镜的衍射极限，纳米尺度形貌的可视化极具挑战性。扫描离子电导显微镜（SICM）是一种在无需标记的条件下可视化细胞表面纳米尺度形貌变化的有效工具。SICM的时间分辨率是活细胞延时成像的关键问题。为此，我们开发了一种新型扫描方法——自动感兴趣区域（AR）模式SICM，通过预测细胞位置来选择下一帧成像区域，从而提高延时成像的扫描速度。新开发的算法将扫描时间缩短了一半。延时图像不仅提供了关于纳米尺度结构变化的新信息，还提供了与记忆密切相关的树突棘和突触小体体积变化以及神经网络形成过程的定量信息。此外，尚未建立荧光标记方法的质膜前体囊泡（ppvs）的转位过程，以及生长锥处细胞骨架的重排，也得到了可视化呈现。

## 框架
研究框架遵循"问题识别 → 技术开发 → 验证与应用"的逻辑主线：

**1. 问题识别**
- 神经元纳米尺度动态结构（树突棘、货物运输、突触形成）与记忆功能密切相关
- 荧光显微镜受衍射极限制约，且荧光蛋白标记可能干扰膜运输过程
- 传统SICM时间分辨率不足，无法满足活细胞延时成像需求
- 神经元具有高纵横比结构（细树突 + 大胞体），给扫描带来额外挑战

**2. 技术开发**
- 开发AR模式扫描算法：利用前一帧图像预测细胞位置，自动选择下一帧扫描区域，减少无效像素扫描
- 开发高谐振频率Z轴压电扫描器（30 kHz），解决Z轴过冲（overshoot）问题，实现真正的非接触成像

**3. 系统验证**
- 对比AR模式与传统扫描模式的扫描时间
- 对比高/低谐振频率Z轴压电器对样品损伤的影响（bleb形成实验）

**4. 生物学应用**
- 树突上微管束及货物运输的可视化
- 树突棘和突触小体的体积变化定量分析
- 生长锥细胞骨架动态重排（P域扩展、板状伪足收缩、肌动蛋白束形成）
- ppvs货物运输的无标记可视化
- 突触形成过程的实时追踪

**5. 结论与展望**
- AR模式SICM作为无标记纳米形貌成像工具的优势总结
- 与共聚焦显微镜联用的互补价值
- 未来与mRNA定位分析结合的潜力

## 研究问题
**核心科学问题：**
如何在不使用荧光标记的前提下，以足够高的时间分辨率对活体海马神经元的纳米尺度动态结构变化进行实时可视化？

**具体子问题：**
1. 如何提高SICM的扫描速度，使其满足神经元动态过程（树突棘变化、货物运输、突触形成）的时间尺度要求？
2. 如何在保证非接触成像的前提下，对具有高纵横比结构的神经元进行高速扫描？
3. 质膜前体囊泡（ppvs）等缺乏特异性生化标记物的细胞结构，能否通过形貌成像直接观测？

**重要性与知识空白：**
- 树突棘的形态变化与突触可塑性（synaptic plasticity）直接相关，是理解学习与记忆机制的关键
- 现有荧光显微镜方法存在两大局限：①衍射极限（~200 nm）无法解析亚微米结构；②荧光蛋白标记可能干扰正常的膜运输过程，且部分分子（如ppvs）尚无可用的荧光标记方案
- 传统SICM虽能实现无标记纳米形貌成像，但扫描速度过慢，无法捕捉神经元的快速动态变化
- 现有高速扫描探针显微镜（如fast-scan AFM，原子力显微镜）在处理神经元这类具有微米级陡峭斜面的结构时仍面临挑战

本文填补了"无标记、纳米分辨率、足够时间分辨率"三者兼顾的神经元活细胞成像技术空白。

## 方法
**1. SICM系统构建**

- 探针：硼硅酸盐玻璃毛细管（GC100F-15，Harvard Apparatus）经CO₂激光拉制仪（P-2000，Sutter Instruments）制备，纳米移液管（nanopipette）开口内径约50 nm
- 电极：Ag/AgCl电极插入纳米移液管，施加电压−0.2 V产生离子电流作为反馈信号
- 电流放大器：自制1 GΩ反馈电阻电流放大器
- Z轴扫描器：自制高谐振频率压电扫描器，电容0.75 μF，谐振频率30 kHz
- 扫描控制：LabVIEW 2014编写控制程序，FPGA（NI USB-7856 OEM）实现实时控制
- 整体平台：搭建于倒置光学显微镜（Nikon ECLIPSE Ti-S）上，置于防振台（Herz TS-150）

**2. AR模式扫描算法**

AR模式的核心步骤：
- 首先采集两帧连续图像，设定三个参数：①平面拟合（plane fit）用于校正样品倾斜；②高度阈值（height threshold，典型值250 nm）用于区分细胞与基底；③图像膨胀（image dilation）用于预测细胞位置变化
- 根据前一帧图像预测细胞所在区域，仅对包含细胞的区域进行扫描，跳过空白基底区域
- 通过"图像膨胀"处理为细胞边界留出余量，以应对细胞形态变化

**3. Hopping模式参数**

- 跳跃幅度（hopping amplitude）：1–3 μm
- 横向移动后等待时间：1 ms（用于测量参考电流IREF）
- 探针下降速度：150–320 nm/ms
- 探针上升速度：1200 nm/ms
- 设定点（set point）：99.3%–99.7% IREF

**4. 海马神经元培养**

- 取材：15天胚龄ICR小鼠海马组织
- 消化：0.25%胰蛋白酶，37°C，20 min
- 铺板密度：1.5 × 10⁴ cells/cm²，铺于poly-L-lysine包被的盖玻片
- 培养基：B-27 Electrophysiology Kit + 青霉素/链霉素/谷氨酰胺，37°C，5% CO₂
- 成像时间点：1、2、4、7、10、14、16、17 DIV（days in vitro，体外培养天数）

**5. SICM与共聚焦显微镜联用**

- 使用MitoTracker Green FM对线粒体进行荧光标记
- 同步采集SICM形貌图像与共聚焦荧光图像，用于鉴定货物运输中的细胞器身份

**6. 对照实验**

- 对比高谐振频率（30 kHz）与低谐振频率（6.2 kHz）Z轴压电器的成像效果，评估Z轴过冲对样品的损伤（bleb形成）
- 采样率：10 kHz（电流与距离信号）

### 关键实验参数
- Nanopipette aperture inner radius：50 nm
- Applied voltage：−0.2 V
- Feedback resistance：1 GΩ
- Z-piezo capacitance：0.75 μF
- Z-piezo resonance frequency (fast)：30 kHz
- Z-piezo resonance frequency (slow, control)：6.2 kHz
- Hopping amplitude：1–3 μm
- Probe falling speed：150–320 nm/ms
- Probe withdrawing speed：1200 nm/ms
- Set point：99.3%–99.7% of IREF
- Lateral movement waiting time：1 ms
- Height threshold (AR mode)：250 nm
- AR-mode scanning time：98 s/frame
- Conventional scanning time：239 s/frame
- High-magnification imaging pixel size：64 × 64
- High-magnification average imaging time：68 s/image
- Scan sizes：5×5, 8×8, 10×10, 15×15, 18×18, 30×30 μm²
- Cell culture density：1.5 × 10⁴ cells/cm²
- Trypsin digestion：0.25%, 37°C, 20 min
- Imaging time points (DIV)：1, 2, 4, 7, 10, 14, 16, 17
- Dendritic spine height：~700 nm
- Dendritic spine width：~500 nm
- Synaptic bouton initial height：~3 μm
- Synaptic bouton final height：~1.5 μm
- P domain recovery time：~135 s
- Cargo transport speed (measured)：0.011 μm/s
- Cargo transport speed (literature reference)：0.91 ± 0.26 μm/s
- Signal sampling rate：10 kHz
- Current amplifier feedback resistance：1 GΩ

## 关键结果
1. **AR模式显著提升扫描速度**：AR模式将单帧扫描时间从239秒缩短至98秒，节省约59%的扫描时间。在一个典型扫描区域中，未扫描像素占51%（8475像素），扫描但无细胞的像素占14%（2318像素），含细胞的有效扫描像素占35%（5591像素），证明AR模式在不丢失结构信息的前提下有效减少了冗余扫描。

2. **微管束及货物运输的无标记可视化**：在16 DIV的海马神经元树突上，SICM直接分辨出微管束（microtubule bundle）的形貌，其形状和尺寸与文献报道一致。延时成像还捕捉到沿微管束的货物运输过程，推测为线粒体介导的运输（通过与MitoTracker荧光共聚焦图像对比确认），测得运输速度约为0.011 μm/s。

3. **树突棘和突触小体的体积变化定量**：在14 DIV神经元中，成功可视化高约700 nm、宽约500 nm的树突棘突起结构。在17 DIV神经元中，观察到突触小体（synaptic bouton）高度从约3 μm自发降低至约1.5 μm，其时间尺度与超分辨率显微镜文献报道一致。

4. **神经网络形成过程的实时追踪**：在突触小体或静脉曲张（varicosity）周围，观察到神经网络形成前肌动蛋白丝（actin filament）的动态重组和肌动蛋白波状传播现象。

5. **生长锥细胞骨架动态重排的多种模式**：
   - 7 DIV神经元：P域（peripheral domain）自发扩展后在约135秒内恢复原状
   - 2 DIV神经元：P域板状伪足（lamellipodia）与周围板状伪足同步收缩
   - 1 DIV神经元：肌动蛋白束（actin bundle）的波状动态重组
   - 多个时间点：生长锥处ppvs货物运输的可视化

6. **突触形成过程的直接观测**：在17 DIV神经元中，观察到片状结构从树突中部出现并延伸至邻近树突，随后形成丝状伪足（filopodia）并与最近的神经突（neurite）粘附，与"丝状伪足模型（filopodial model）"吻合。在10 DIV神经元中，还观察到丝状伪足多次触碰同一位点并最终形成突触的过程。

7. **高谐振频率Z轴压电器对非接触成像的必要性**：使用低谐振频率（6.2 kHz）Z轴压电器时，过冲持续约0.6 ms，导致纳米移液管与样品接触，在神经突上诱发出泡（bleb）形成；而高谐振频率（30 kHz）压电器将过冲时间压缩至约0.2 ms，有效避免了样品损伤。

## 创新点
**1. AR模式扫描算法（核心创新）**
这是本文最主要的方法学创新。与此前的预扫描方法（Novak等人通过预扫描改变像素大小）不同，AR模式利用前一帧图像的高度信息实时预测细胞位置，通过图像膨胀处理自动划定下一帧的扫描边界，无需额外的预扫描步骤。这一算法将扫描时间减半，且对细胞结构无损伤风险（相比之前作者自己开发的跳跃幅度优化算法，AR模式消除了与样品碰撞的可能性，更适合树突棘等脆弱浮动结构）。

**2. 高谐振频率Z轴压电扫描器**
自制的30 kHz谐振频率Z轴压电扫描器（电容仅0.75 μF）显著减少了hopping模式中的Z轴过冲问题，将过冲时间从0.6 ms压缩至0.2 ms，实现了对脆弱神经元的真正非接触成像。这是对此前双Z轴压电系统（Shevchuk等人）和turn-step协议（Simeonov和Schäffer）的进一步改进。

**3. ppvs的无标记直接可视化**
质膜前体囊泡（ppvs）目前尚无成熟的荧光标记方案，只能通过脉冲标记策略间接研究。本文首次通过SICM形貌成像直接观测到ppvs在生长锥处的运输动态，展示了SICM在研究缺乏特异性标记物的细胞结构方面的独特优势。

**4. 神经元结构动态的定量分析**
不同于以往SICM研究主要停留在定性形貌描述，本文提供了树突棘尺寸（高700 nm，宽500 nm）、突触小体体积变化（高度从3 μm降至1.5 μm）、P域恢复时间（约135秒）等定量数据，为神经科学研究提供了可与超分辨率显微镜结果直接比较的定量指标。

**5. SICM与共聚焦显微镜的联用策略**
通过同步采集SICM形貌图像和MitoTracker荧光图像，建立了形貌特征与细胞器身份之间的对应关系，为后续利用SICM形貌信息推断细胞器类型提供了方法论基础。

## 局限性
**1. 时间分辨率仍有不足**
尽管AR模式将扫描时间缩短了一半，但对于快速货物运输（文献报道线粒体运输速度约0.91 μm/s）仍然太慢。本文实测的货物运输速度仅为0.011 μm/s，作者将其归因于捕获了低运动性线粒体，但这也说明当前系统无法可靠地追踪正常速度的货物运输事件。

**2. AR模式的局限性**
AR模式依赖前一帧图像预测细胞位置，当细胞形态变化超出预测范围，或成像范围外的结构进入视野时，会出现漏扫情况。作者建议通过比较多帧连续图像并手动调整来应对，但这增加了操作复杂性，也限制了完全自动化的可能性。

**3. 成像范围与分辨率的权衡**
高速成像需要减少像素数（如64×64），而高分辨率成像需要更多像素，两者存在固有矛盾。对于需要同时覆盖大范围（如整个神经元）和高分辨率（如单个树突棘）的实验，当前系统难以兼顾。

**4. 细胞器身份鉴定依赖联用技术**
SICM本身只能提供形貌信息，无法直接鉴定观测到的结构的分子身份。货物运输中的细胞器类型需要借助共聚焦显微镜联用才能确认，而ppvs的鉴定仍主要依赖形态学推断，缺乏直接的分子证据。

**5. 样品制备的局限性**
实验使用体外培养的原代海马神经元，与体内神经元的生理状态存在差异。培养条件（密度、培养基成分等）可能影响神经元的形态动态，实验结果向体内情况的外推需谨慎。

**6. 三维结构信息不完整**
SICM只能获取细胞表面的形貌信息，无法直接观测细胞内部结构。对于树突棘体积变化的分析，仅基于表面高度和宽度的测量，可能低估或高估真实的体积变化。

**7. 扫描速度与样品损伤的平衡**
提高扫描速度需要增大探针下降速度，这会增加与样品接触的风险。尽管高谐振频率Z轴压电器减少了过冲，但在极高速扫描条件下，非接触成像的保证仍需进一步验证。


## 值得追踪的参考文献
- (1) Hansma, P. K.; Drake, B.; Marti, O.; Gould, S. A. C.; Prater, C. B. Science 1989, 243, 641−643.
- 【SICM技术的奠基性论文，首次提出扫描离子电导显微镜的概念】
- (2) Novak, P.; Li, C.; Shevchuk, A. I.; Stepanyan, R.; Caldwell, M.; Hughes, S.; Smart, T. G.; Gorelik, J.; Ostanin, V. P.; Lab, M. J.; Moss, G. W. J.; Frolenkov, G. I.; Klenerman, D.; Korchev, Y. E. Nat. Methods 2009, 6, 279−281.
- 【Hopping模式SICM及预扫描方法的关键前驱工作，本文AR模式的直接改进对象】
- (3) Shevchuk, A. I.; Novak, P.; Taylor, M.; Diakonov, I. A.; Ziyadeh-Isleem, A.; Bitoun, M.; Guicheney, P.; Lab, M. J.; Gorelik, J.; Merrifield, C. J.; Klenerman, D.; Korchev, Y. E. J. Cell Biol. 2012, 197, 499−508.
- 【双Z轴压电系统的开发，解决hopping模式过冲问题的重要前驱工作】
- (4) Zhou, Y. S.; Saito, M.; Miyamoto, T.; Novak, P.; Shevchuk, A. I.; Korchev, Y. E.; Fukuma, T.; Takahashi, Y. Anal. Chem. 2018, 90, 2891−2895.
- 【本文作者团队的前期工作，建立了SICM非接触成像的操作规范，是本文方法的直接基础】
- (5) Kasai, H.; Fukuda, M.; Watanabe, S.; Hayashi-Takagi, A.; Noguchi, J. Trends Neurosci. 2010, 33, 121−129.
- 【树突棘结构变化与记忆关系的重要综述，为本文的生物学背景提供核心依据】
- (6) Ida, H.; Takahashi, Y.; Kumatani, A.; Shiku, H.; Matsue, T. Anal. Chem. 2017, 89, 6015−6020.
- 【本文作者团队开发的跳跃幅度优化算法，是AR模式的直接前驱，本文在此基础上进一步改进】
- (7) Chéreau, R.; Saraceno, G. E.; Angibaud, J.; Cattaert, D.; Nägerl, U. V. Proc. Natl. Acad. Sci. U. S. A. 2017, 114, 1401−1406.
- 【使用超分辨率显微镜研究突触小体动态变化的关键对照文献，本文SICM结果与之进行了直接比较】
- (8) Shibata, M.; Uchihashi, T.; Ando, T.; Yasuda, R. Sci. Rep. 2015, 5, 08724.
- 【高速AFM（原子力显微镜）成像海马神经元的代表性工作，是本文SICM方法的主要竞争技术参照】
