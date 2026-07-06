# Changelog

## [1.20.0](https://github.com/im-anishraj/arnio/compare/v1.19.0...v1.20.0) (2026-06-30)


### Features

* accept tuple subsets in round_numeric_columns ([#2031](https://github.com/im-anishraj/arnio/issues/2031)) ([39b96a9](https://github.com/im-anishraj/arnio/commit/39b96a907dc5bced2fccef8359b1d4598dd6b11a))
* add chunked JSONL reader ([#2294](https://github.com/im-anishraj/arnio/issues/2294)) ([369a34b](https://github.com/im-anishraj/arnio/commit/369a34b1173dabefe7bbd2d1f62dd86e632743da))
* Add compressed CSV support for .csv.gz files ([2e3fdc2](https://github.com/im-anishraj/arnio/commit/2e3fdc2158a2118fba25c14ba8879428097fdf86))
* add custom 404 page ([#2292](https://github.com/im-anishraj/arnio/issues/2292)) ([fff4d89](https://github.com/im-anishraj/arnio/commit/fff4d89d73fd71cd44707fef86bc95f27674b991))
* add docs and API search ([#2346](https://github.com/im-anishraj/arnio/issues/2346)) ([b62b359](https://github.com/im-anishraj/arnio/commit/b62b3597292ed31090b5387e61c1fcfc991b86c8))
* add drop_empty_columns cleaning step ([#375](https://github.com/im-anishraj/arnio/issues/375)) ([08366e1](https://github.com/im-anishraj/arnio/commit/08366e1cc1db567e494b281c0a1339c076f9a112))
* add duckdb optional dependency extra ([#2246](https://github.com/im-anishraj/arnio/issues/2246)) ([0af1faf](https://github.com/im-anishraj/arnio/commit/0af1faf4e199b96e12757ed973a47d51d3bbf440))
* add execution_summary to return_metadata diagnostics ([#2317](https://github.com/im-anishraj/arnio/issues/2317)) ([5871d9a](https://github.com/im-anishraj/arnio/commit/5871d9acc742b161789e42795127b52db0229cf9))
* add from_arrow helper ([#2296](https://github.com/im-anishraj/arnio/issues/2296)) ([9d5a235](https://github.com/im-anishraj/arnio/commit/9d5a235c84027a87127f17ab900e12c658c4a620))
* add hash_columns pipeline step ([#2522](https://github.com/im-anishraj/arnio/issues/2522)) ([b0b7f2c](https://github.com/im-anishraj/arnio/commit/b0b7f2cb065fcb6fb9b38ed0a9eafbd79e43e86d))
* add IQR outlier summary to column profiles ([#1003](https://github.com/im-anishraj/arnio/issues/1003)) ([80c5ead](https://github.com/im-anishraj/arnio/commit/80c5ead242d2a319a25e7f4bdb2aaa950b21aa95))
* add normalize_minmax cleaning primitive ([#2422](https://github.com/im-anishraj/arnio/issues/2422)) ([c4b84e1](https://github.com/im-anishraj/arnio/commit/c4b84e11ae8a36d94d207dc1e44924eca1cad264))
* add orient support to ArFrame.to_dict ([#2108](https://github.com/im-anishraj/arnio/issues/2108)) ([7b9e6fe](https://github.com/im-anishraj/arnio/commit/7b9e6fe7bcff02ea344a4cb712c964ac951e847e))
* add rename_columns_matching for regex-based bulk column renaming ([#1560](https://github.com/im-anishraj/arnio/issues/1560)) ([26584d8](https://github.com/im-anishraj/arnio/commit/26584d85050d5e862f035c181a5a57a2e266e915))
* add row lineage metadata through filtering and drop steps ([1f07484](https://github.com/im-anishraj/arnio/commit/1f07484e43544f1e9c02fa29403bed47ce6df3ae))
* add row lineage metadata through filtering and drop steps ([de32617](https://github.com/im-anishraj/arnio/commit/de326173f7ef937f615752942c606deba1cf1639))
* add row lineage metadata through filtering and drop steps (review changes) ([fc30e05](https://github.com/im-anishraj/arnio/commit/fc30e05416db7c4cc7e39bb6d927c1742ca8a11e))
* add scan_csv permissive mode parity ([#1998](https://github.com/im-anishraj/arnio/issues/1998)) ([2f8bcbe](https://github.com/im-anishraj/arnio/commit/2f8bcbecdbd776eb55fb8380fac81d4f5765cd9f))
* add score breakdown API to DataQualityReport ([4358028](https://github.com/im-anishraj/arnio/commit/43580283d59b043a9ea93bb98653057fa742af0a))
* add score breakdown API to DataQualityReport ([7d8a003](https://github.com/im-anishraj/arnio/commit/7d8a0032aa0c4989bea43db1645c570cea3561ab))
* add slugify_column_names cleaning primitive and pipeline step ([#1718](https://github.com/im-anishraj/arnio/issues/1718)) ([0f1490d](https://github.com/im-anishraj/arnio/commit/0f1490dcb9c3f2c52ce28e5ab433cee8d21e5719))
* add string length validation tests ([#2028](https://github.com/im-anishraj/arnio/issues/2028)) ([1cc500d](https://github.com/im-anishraj/arnio/commit/1cc500d85fb09e665fe8aa5bcf399c4f9fba4bca))
* add title and camel case_types to clean_column_names ([#2541](https://github.com/im-anishraj/arnio/issues/2541)) ([#2543](https://github.com/im-anishraj/arnio/issues/2543)) ([dcc0302](https://github.com/im-anishraj/arnio/commit/dcc03023a6a5c0e070f03685e6b8a8473633f719))
* add to_csv convenience method directly on ArFrame ([ef2a02e](https://github.com/im-anishraj/arnio/commit/ef2a02e3c1f57e588c163db721482ad267385dfd)), closes [#1981](https://github.com/im-anishraj/arnio/issues/1981)
* Add to_csv() convenience method directly on ArFrame ([bf965b9](https://github.com/im-anishraj/arnio/commit/bf965b9e041152c1b1608ff224e7f668a14284f6))
* add UUID, IPv4, and MACAddress semantic validators ([#2520](https://github.com/im-anishraj/arnio/issues/2520)) ([1de3205](https://github.com/im-anishraj/arnio/commit/1de3205e0ea4805798b0a18048be0574ec5cc9d4))
* add validate_chunked for large CSV validation ([125bbe6](https://github.com/im-anishraj/arnio/commit/125bbe69f8c8afe93d30bc3479b79e94b1c80e57))
* add validate_chunked() and profile_chunked() for large CSV files ([#861](https://github.com/im-anishraj/arnio/issues/861)) ([894e549](https://github.com/im-anishraj/arnio/commit/894e549a60f28762b33ea606ff3483fedbc7fd6c))
* add write_json support ([#2481](https://github.com/im-anishraj/arnio/issues/2481)) ([c2bfd99](https://github.com/im-anishraj/arnio/commit/c2bfd99fe32e4f83ec9b76625759bb27c093415d))
* clean api enhancement ([#2267](https://github.com/im-anishraj/arnio/issues/2267)) ([c7502df](https://github.com/im-anishraj/arnio/commit/c7502df7e2e0b3aebfe5369f764351419b11816f))
* **cleaning:** add cast_types error policies ([5a601fe](https://github.com/im-anishraj/arnio/commit/5a601fe35680333d67aec5a05a5320c0685629a6))
* **cleaning:** add fuzzy duplicate detection ([67715a1](https://github.com/im-anishraj/arnio/commit/67715a1fb6b2c8511cd4ce323cce1220ecb77d36))
* **cli:** add arnio scan command ([#2297](https://github.com/im-anishraj/arnio/issues/2297)) ([19fdad7](https://github.com/im-anishraj/arnio/commit/19fdad752d5dfb1eb148ee3b6ec3e812af1a46ee))
* **convert:** preserve attrs metadata in to_arrow ([aed9354](https://github.com/im-anishraj/arnio/commit/aed935407132fb946b85c8f05caebc7ddb220ffe))
* export CleaningSuggestion from the top-level API (fixes [#1963](https://github.com/im-anishraj/arnio/issues/1963)) ([#2024](https://github.com/im-anishraj/arnio/issues/2024)) ([c017875](https://github.com/im-anishraj/arnio/commit/c0178757cd2c0fa52f58ddbbd4945d9344b78099))
* extend df.arnio cleaning wrappers ([#1606](https://github.com/im-anishraj/arnio/issues/1606)) ([#1618](https://github.com/im-anishraj/arnio/issues/1618)) ([e7d7f9d](https://github.com/im-anishraj/arnio/commit/e7d7f9dc2bb81b39fc0e1a7504f9b0abb2332372))
* implement declarative pipeline serialization (strictly additive) ([#2104](https://github.com/im-anishraj/arnio/issues/2104)) ([ebd54eb](https://github.com/im-anishraj/arnio/commit/ebd54ebfa70c8a883ae0b4f86387f878b36eb25d))
* implement fail-fast boundary validation in register_step ([#721](https://github.com/im-anishraj/arnio/issues/721)) ([#1485](https://github.com/im-anishraj/arnio/issues/1485)) ([cd52508](https://github.com/im-anishraj/arnio/commit/cd52508011d38c921b4a6e80627cd9d5953bd254))
* improve footer ui and social links ([#1450](https://github.com/im-anishraj/arnio/issues/1450)) ([fbb42c4](https://github.com/im-anishraj/arnio/commit/fbb42c40eff209a3cb0d4fc584fd8806f0585dc8))
* include bool columns in describe ([#2012](https://github.com/im-anishraj/arnio/issues/2012)) ([2f9119b](https://github.com/im-anishraj/arnio/commit/2f9119b2ea56bfe2bad1d9ab98f87a7328698d27))
* **integrations:** add Polars Arrow bridge ([#2305](https://github.com/im-anishraj/arnio/issues/2305)) ([8bce4b7](https://github.com/im-anishraj/arnio/commit/8bce4b7e3606a3093ccb32a176bcbca053f617f6))
* **integrations:** add to_polars and from_polars via Arrow bridge ([ca77a1b](https://github.com/im-anishraj/arnio/commit/ca77a1ba73241532794881713ef2639d46a288a4))
* **integrations:** add to_polars and from_polars via Arrow bridge (review changes) ([5ff983a](https://github.com/im-anishraj/arnio/commit/5ff983a99b14402cf1cbc53af6c8ade1eec5aa5b))
* **integrations:** expose ArnioCleaner lazily ([#2053](https://github.com/im-anishraj/arnio/issues/2053)) ([7eb7a88](https://github.com/im-anishraj/arnio/commit/7eb7a88cf3a790337a4c27d4d26db7c5f67c5b5d))
* **io:** add encoding and encoding_errors params to write_csv() ([#2485](https://github.com/im-anishraj/arnio/issues/2485)) ([b9c2b65](https://github.com/im-anishraj/arnio/commit/b9c2b6553e56f1d0a05226ccf4038b827dffd188))
* **io:** add read_parquet() via Arrow bridge ([ece788a](https://github.com/im-anishraj/arnio/commit/ece788ac7c09acac8699654857180374bb3c23c5))
* **io:** add read_parquet() via Arrow bridge ([9ea39f0](https://github.com/im-anishraj/arnio/commit/9ea39f0472c93ca2c3fc495283e30133322e7418))
* **io:** add read_parquet() via Arrow bridge (review changes) ([64df078](https://github.com/im-anishraj/arnio/commit/64df078cf92f54de028087017d361a857d5f4a7b))
* **io:** add read_parquet() via Arrow bridge (review changes) ([bd5f103](https://github.com/im-anishraj/arnio/commit/bd5f1034e7ab87d5b29ffe465f37bd83d9985f62))
* **jsonl:** support encoding error handling ([#2040](https://github.com/im-anishraj/arnio/issues/2040)) ([8651420](https://github.com/im-anishraj/arnio/commit/86514201597cb9bfb2d4f75d921297d9e93083f6))
* optimize drop_duplicates hashing ([89a895a](https://github.com/im-anishraj/arnio/commit/89a895a82faf245d6df4385e0f550042f1f49fd7))
* **quality:** add detect_drift() and DriftReport for dataset drift detection ([#2537](https://github.com/im-anishraj/arnio/issues/2537)) ([41d314e](https://github.com/im-anishraj/arnio/commit/41d314e2116e5a4067452484b96de35dd7eca588))
* **quality:** support Markdown column exclusions ([de765a8](https://github.com/im-anishraj/arnio/commit/de765a8f55399d4dd5c6a7f3880c3e74577ef33f))
* **schema:** add min and max bounds to Date() field ([#2514](https://github.com/im-anishraj/arnio/issues/2514)) ([b1d4b38](https://github.com/im-anishraj/arnio/commit/b1d4b3861dcd3dc2ccf90c1083a6c8d5922d458e))
* **schema:** add schema_from_yaml loader as inverse of schema_to_yaml ([#2483](https://github.com/im-anishraj/arnio/issues/2483)) ([3eb48a3](https://github.com/im-anishraj/arnio/commit/3eb48a340841e578ebc1058f50242de953e41a57))
* **sklearn:** enforce schema-stability contract in ArnioCleaner ([#946](https://github.com/im-anishraj/arnio/issues/946)) ([#1036](https://github.com/im-anishraj/arnio/issues/1036)) ([fc27829](https://github.com/im-anishraj/arnio/commit/fc278291b2eb87aa39dfc1d71003c0a1722e5ef3))
* support column exclusions in profile comparison markdown ([7f6cd2a](https://github.com/im-anishraj/arnio/commit/7f6cd2ae72bb8156a3d44236fdff8d9751e49e39))
* support file-like inputs in scan_csv ([#2238](https://github.com/im-anishraj/arnio/issues/2238)) ([e01c564](https://github.com/im-anishraj/arnio/commit/e01c56483dfdf5dd6e5651bdea52f16f1087a070))
* **website:** add comparison section with visual contrast ([34d1098](https://github.com/im-anishraj/arnio/commit/34d1098c1e7ab9dc5c7c802822c46d6219668331))


### Bug Fixes

* **a11y:** respect reduced motion preference for anchor scrolling ([#2179](https://github.com/im-anishraj/arnio/issues/2179)) ([2d09073](https://github.com/im-anishraj/arnio/commit/2d090737402e25380fba41dd8769a0c682d66bbb)), closes [#2172](https://github.com/im-anishraj/arnio/issues/2172)
* add __post_init__ validation to CleanStepRecord and CleanExplanation ([#1987](https://github.com/im-anishraj/arnio/issues/1987)) ([a636f9c](https://github.com/im-anishraj/arnio/commit/a636f9c992afcf0f41ec1de45013f95ed7033fb3))
* add caller-specific TypeError messages and document RemoteReadError ([#731](https://github.com/im-anishraj/arnio/issues/731)) ([b899c34](https://github.com/im-anishraj/arnio/commit/b899c341e585a6350b303259320257778265a1ad))
* add clear path type errors in path-only readers ([fd860c1](https://github.com/im-anishraj/arnio/commit/fd860c1d71b3d15a3c10df1daa1734636d33cba6))
* add clear path type errors in path-only readers ([32798db](https://github.com/im-anishraj/arnio/commit/32798dbad9f0631e7984c0f0d67af39df0e82471))
* add CLI help guards to older benchmark scripts ([#2025](https://github.com/im-anishraj/arnio/issues/2025)) ([3099fc5](https://github.com/im-anishraj/arnio/commit/3099fc5f4d9cf51a80480dad13d1965861193500))
* add context to custom validator errors ([609120c](https://github.com/im-anishraj/arnio/commit/609120cd978794fd26c7c68ebe98c8cf30705b1d))
* add context to custom validator errors ([7c60ec6](https://github.com/im-anishraj/arnio/commit/7c60ec6efed03cfa1816629945fc37bc6976ef06))
* add deterministic report representation for notebooks and terminals ([#972](https://github.com/im-anishraj/arnio/issues/972)) ([6182ac1](https://github.com/im-anishraj/arnio/commit/6182ac17a1b01fdbfbfbbef8a03f78131098a7cb))
* add Escape key support and sync aria-label for mobile menu ([#2100](https://github.com/im-anishraj/arnio/issues/2100)) ([c7ee2fb](https://github.com/im-anishraj/arnio/commit/c7ee2fb597835a8f6604f1e30e91147be343a9c7))
* add from __future__ import annotations to exceptions.py for Python 3.9 compat ([3f4037a](https://github.com/im-anishraj/arnio/commit/3f4037a275cfd5411805ea275401dc6ee63e270f))
* add opt-in csv formula escaping ([#2301](https://github.com/im-anishraj/arnio/issues/2301)) ([91b4418](https://github.com/im-anishraj/arnio/commit/91b44185ea9c3f7566cf47c495d08c3067429a7c))
* add page-specific canonical and Open Graph URLs ([#2538](https://github.com/im-anishraj/arnio/issues/2538)) ([e9b093b](https://github.com/im-anishraj/arnio/commit/e9b093b8ed8bc2cd3c881f613e964586c22b0350))
* address review blockers for score_breakdown and extend regression tests ([a5326ec](https://github.com/im-anishraj/arnio/commit/a5326ece020f76c71ef8dbdec5fe217633c78e94))
* align issue template labels with live taxonomy (Fixes [#1372](https://github.com/im-anishraj/arnio/issues/1372)) ([#2187](https://github.com/im-anishraj/arnio/issues/2187)) ([55a708c](https://github.com/im-anishraj/arnio/commit/55a708c120d0bda690c80d2f82976f8fdae7700c))
* align score_breakdown tests with implementation ([2e70f61](https://github.com/im-anishraj/arnio/commit/2e70f61c540150253177f76dd7bef53cc452d4bf))
* allow tuple input in ArFrame.drop_columns ([#2011](https://github.com/im-anishraj/arnio/issues/2011)) ([68ae15f](https://github.com/im-anishraj/arnio/commit/68ae15f4449a1cf300b76e1b147c8637e1c9f842))
* allow unregistering custom aliases of built-in cleaning steps ([#2008](https://github.com/im-anishraj/arnio/issues/2008)) ([3a303f1](https://github.com/im-anishraj/arnio/commit/3a303f14e0a59eaad7fb02b4f9ebd64c75abb4ea))
* ArFrame.astype leaks pd.NA ambiguous truth-value errors ([#2536](https://github.com/im-anishraj/arnio/issues/2536)) ([f33cec3](https://github.com/im-anishraj/arnio/commit/f33cec3c2633b89c2339aa1479167da04f138015))
* **asan:** reject bool fill values for numeric columns before entering C++ ([#2286](https://github.com/im-anishraj/arnio/issues/2286)) ([abf80cf](https://github.com/im-anishraj/arnio/commit/abf80cf641c1e8d89436f0c354a31fd959b24b21))
* avoid returning original frame from drop_empty_columns zero-row path ([#1996](https://github.com/im-anishraj/arnio/issues/1996)) ([78fdccc](https://github.com/im-anishraj/arnio/commit/78fdccc5d274a256f5c0e93c020b7b66043c3fe8))
* break on max_errors, drop profile_chunked pending contract proposal ([f6be7e9](https://github.com/im-anishraj/arnio/commit/f6be7e940b6346d8b56bb8d0bf48c95c0f66ea15))
* broken Open Graph social preview image URL ([#2484](https://github.com/im-anishraj/arnio/issues/2484)) ([64e6b9b](https://github.com/im-anishraj/arnio/commit/64e6b9b197c5a160a66e91360d8203aabc2b2e52))
* caller-specific TypeError messages and RemoteReadError in API docs ([#731](https://github.com/im-anishraj/arnio/issues/731)) ([2d7e2f0](https://github.com/im-anishraj/arnio/commit/2d7e2f007ae560e4b3863cc6d321e17e0b726871))
* change 404 heading from h2 to h1 for accessibility ([#2437](https://github.com/im-anishraj/arnio/issues/2437)) ([#2616](https://github.com/im-anishraj/arnio/issues/2616)) ([8f78a52](https://github.com/im-anishraj/arnio/commit/8f78a524f52063dd87620224ea6831f2c786caef))
* clarify HTML repr for non-empty zero-column frames ([#2124](https://github.com/im-anishraj/arnio/issues/2124)) ([2750075](https://github.com/im-anishraj/arnio/commit/2750075d6518056a0a05a7050341611c353d2400))
* **cleaning:** raise TypeError for non-scalar replace_values mapping keys ([#2263](https://github.com/im-anishraj/arnio/issues/2263)) ([53749ea](https://github.com/im-anishraj/arnio/commit/53749ea309232d611a065ca872658b2820634598))
* **cleaning:** return new frame from winsorize no-op path ([d98c8fd](https://github.com/im-anishraj/arnio/commit/d98c8fd2a0238029031066028c255c608cfd51e5))
* **cleaning:** validate normalize_unicode form type ([5236f49](https://github.com/im-anishraj/arnio/commit/5236f49921834bd40ba248c8dbdd3bb14fd13648))
* **cleaning:** validate safe_divide_columns column name types ([#2107](https://github.com/im-anishraj/arnio/issues/2107)) ([3f8b640](https://github.com/im-anishraj/arnio/commit/3f8b6407a2ab0a2945c088e9b8c0b298499882a6))
* clone clean column names noop ([#2029](https://github.com/im-anishraj/arnio/issues/2029)) ([444cb80](https://github.com/im-anishraj/arnio/commit/444cb801d6ada21c0e3add4cadb5ee17126dff81))
* close docs search after result selection ([#2548](https://github.com/im-anishraj/arnio/issues/2548)) ([94939fc](https://github.com/im-anishraj/arnio/commit/94939fce0e39507bbb152972e9a8b69f637daeb3))
* **convert:** validate scalar values in from_dict ([#2151](https://github.com/im-anishraj/arnio/issues/2151)) ([af8878a](https://github.com/im-anishraj/arnio/commit/af8878a33455c3827dd02a52037f2efc4041fb98)), closes [#1653](https://github.com/im-anishraj/arnio/issues/1653)
* **csv-parser:** prioritize structural consistency over raw frequency… ([#2335](https://github.com/im-anishraj/arnio/issues/2335)) ([1785ac5](https://github.com/im-anishraj/arnio/commit/1785ac55d42f907b89096e0d3fcd14ae18a1239a))
* **csv:** improve validation error diagnostics ([#2498](https://github.com/im-anishraj/arnio/issues/2498)) ([854bff4](https://github.com/im-anishraj/arnio/commit/854bff480fcb2137abe77c528977f7929050dce7))
* **csv:** preserve mid-field quotes ([#1993](https://github.com/im-anishraj/arnio/issues/1993)) ([2810f7a](https://github.com/im-anishraj/arnio/commit/2810f7aff05925c396fe63012685c84f988da747))
* **csv:** use shared delimiter validation in write_csv ([#2121](https://github.com/im-anishraj/arnio/issues/2121)) ([8642d9d](https://github.com/im-anishraj/arnio/commit/8642d9d2b5094df39ceba53768db8eb2c5e91581))
* DataQualityReport.to_pandas ([#2148](https://github.com/im-anishraj/arnio/issues/2148)) ([4706777](https://github.com/im-anishraj/arnio/commit/47067773bb79387856f8a29b94b86052ef1cf807))
* deduplicate strict auto_clean after normalization ([2c1fb60](https://github.com/im-anishraj/arnio/commit/2c1fb6030eecbd7b650dbd11ce2eab51b5868794))
* deduplicate strict auto_clean after normalization ([c947eb4](https://github.com/im-anishraj/arnio/commit/c947eb4727160ed7c69eaf08688c5a6783e33a21))
* defer ArnioCleaner param validation to fit/transform ([#1959](https://github.com/im-anishraj/arnio/issues/1959)) ([3bda610](https://github.com/im-anishraj/arnio/commit/3bda610d64533e05c612972386dfd9171ffd7621))
* deterministic sort for mixed-type allowed values ([#2017](https://github.com/im-anishraj/arnio/issues/2017)) ([121f121](https://github.com/im-anishraj/arnio/commit/121f1216eec95f58ca4e9a6e12ba23211deb53b6))
* fixed Data loss in normalize_whitespace ([ba3bfe4](https://github.com/im-anishraj/arnio/commit/ba3bfe4cc7b930a49270cb761cb72dd2a63a1424))
* forced bool dtype raises CsvReadError for invalid non-null tokens ([#2001](https://github.com/im-anishraj/arnio/issues/2001)) ([e6002ea](https://github.com/im-anishraj/arnio/commit/e6002ea98516ea9f8b05e7f1b723da1064b1108a))
* **frame:** handle non-finite float values in describe ([#2002](https://github.com/im-anishraj/arnio/issues/2002)) ([7fe483c](https://github.com/im-anishraj/arnio/commit/7fe483c875001a5b4f3e74e4cc3e6ccf2b30890a))
* **frame:** preserve attrs in head and tail ([#2055](https://github.com/im-anishraj/arnio/issues/2055)) ([5dd47a0](https://github.com/im-anishraj/arnio/commit/5dd47a07a420d138037d6d08205e0f33697f515b))
* guard unsafe float to int64 casts ([#2003](https://github.com/im-anishraj/arnio/issues/2003)) ([8dfdd96](https://github.com/im-anishraj/arnio/commit/8dfdd96d7f9b9e56fe2c1dc9afa34dfff6fae76d))
* handle malformed benchmark entries safely ([a7e276b](https://github.com/im-anishraj/arnio/commit/a7e276bf47507c3fca4e4bf68df118c79a72167b))
* handle malformed benchmark entries safely ([ee17385](https://github.com/im-anishraj/arnio/commit/ee1738552dfcb8e6a0f71c65ee62cfab68c0c4c2))
* handle non-json attrs in parquet export ([c1f014b](https://github.com/im-anishraj/arnio/commit/c1f014b331d4ea4fc3fe5cdaed542bb80dceedde)), closes [#1907](https://github.com/im-anishraj/arnio/issues/1907)
* handle zero-column frames in drop_columns_matching ([#2215](https://github.com/im-anishraj/arnio/issues/2215)) ([0070340](https://github.com/im-anishraj/arnio/commit/0070340ad3c5b2694b6ba291c63d9827f69bf488))
* handle zero-column frames in preview ([#1548](https://github.com/im-anishraj/arnio/issues/1548)) ([e3f71e2](https://github.com/im-anishraj/arnio/commit/e3f71e292423fe843c130c2be2610f15942359d7))
* honor case-insensitive semantic code validation ([c4a4cfb](https://github.com/im-anishraj/arnio/commit/c4a4cfb4f6eafc350b22b5c9b8c3ddd55dcca9c8))
* Improving invalid utf-8 error reporting along with regression tests ([#2521](https://github.com/im-anishraj/arnio/issues/2521)) ([f942dec](https://github.com/im-anishraj/arnio/commit/f942dec86f66e342dd72e785de42d1574b3b246b))
* include website text assets in UTF-8 validation ([#2110](https://github.com/im-anishraj/arnio/issues/2110)) ([3368e59](https://github.com/im-anishraj/arnio/commit/3368e593f3a9e716695a96eaf4399f51032578f5))
* incremental UTF-8 decode in fetch + restore aria-labels + split-char tests ([9c69072](https://github.com/im-anishraj/arnio/commit/9c69072f6345abd807d496bdf1ad41463df4a9fa))
* incremental UTF-8 decode in fetch + restore aria-labels + split-char tests (lint fix) ([0636a5d](https://github.com/im-anishraj/arnio/commit/0636a5d3ac2f483fa3dd05afb03681b5d2e71fd0))
* initialize MSVC in windows wheel smoke workflow ([#2490](https://github.com/im-anishraj/arnio/issues/2490)) ([eafe62f](https://github.com/im-anishraj/arnio/commit/eafe62fa12b9b83169b562dd12a7976d5fa46036))
* **integrations:** reject whitespace-only DuckDB relation names ([#2116](https://github.com/im-anishraj/arnio/issues/2116)) ([14733ae](https://github.com/im-anishraj/arnio/commit/14733ae8701178919b6bc94883f0888bb6ed9499))
* **io:** handle GeneratorExit in read_csv_chunked for deterministic e… ([#2343](https://github.com/im-anishraj/arnio/issues/2343)) ([b18a342](https://github.com/im-anishraj/arnio/commit/b18a3425849852b6fb2cb5b46822fe223ee95558))
* **io:** prevent temp file leak when close() raises in _materialize_c… ([#2249](https://github.com/im-anishraj/arnio/issues/2249)) ([636e737](https://github.com/im-anishraj/arnio/commit/636e737bdeb0f3681570cce8c3928b49e6f55553))
* **io:** validate parquet compression argument type ([f6249bc](https://github.com/im-anishraj/arnio/commit/f6249bc6c2bad18128182adea32ae6d1830bb0e5))
* make code block copy buttons visible on keyboard focus ([#1992](https://github.com/im-anishraj/arnio/issues/1992)) ([16251f7](https://github.com/im-anishraj/arnio/commit/16251f79ae09486b5991bfd569333f53204afb29))
* make CSV transcoding writes atomic ([#2491](https://github.com/im-anishraj/arnio/issues/2491)) ([53d869d](https://github.com/im-anishraj/arnio/commit/53d869db8b4d18bfcd35d019be67f857fa991142))
* make custom pipeline step frames writable ([70134f0](https://github.com/im-anishraj/arnio/commit/70134f0849da992b248733a19b61123c02e42972))
* normalize data quality suggestion kwargs for JSON ([#2544](https://github.com/im-anishraj/arnio/issues/2544)) ([31b13dc](https://github.com/im-anishraj/arnio/commit/31b13dc2e9e196af23ed13db49d9cc2adf960cd0))
* optimize website logo assets ([#2220](https://github.com/im-anishraj/arnio/issues/2220)) ([0fe9bf2](https://github.com/im-anishraj/arnio/commit/0fe9bf221716c3e8f147d4ee3da8d5785c352b21))
* **pipeline:** protect Python-backed built-in steps ([adf372f](https://github.com/im-anishraj/arnio/commit/adf372f3696a69546bad204923c33a2b31aefb79))
* **pipeline:** reject ambiguous cast_types shorthand kwargs ([b9c3aec](https://github.com/im-anishraj/arnio/commit/b9c3aecdfb65053ba2a506a6809901481fecc476))
* preserve arrow rows for zero-column frames ([bae3fbd](https://github.com/im-anishraj/arnio/commit/bae3fbd56fc145a36befa7f84eb0d7224666bc71))
* preserve attrs in drop_duplicates zero-column path ([0e2162e](https://github.com/im-anishraj/arnio/commit/0e2162efe92ac79e6208b1291765c26ad42a83b0))
* preserve attrs metadata in ArFrame selection methods ([#1999](https://github.com/im-anishraj/arnio/issues/1999)) ([17aa4a5](https://github.com/im-anishraj/arnio/commit/17aa4a552908845f3c7c3cda589f147efc1085c7))
* preserve chunked csv streaming validation ([5d7c2fb](https://github.com/im-anishraj/arnio/commit/5d7c2fb8b4cf1e0c2d5bde493007b6d67e777d90))
* preserve chunked csv streaming validation ([c58654c](https://github.com/im-anishraj/arnio/commit/c58654c4464139fe20e5229c614a582943d5e6b1))
* preserve CSV validation errors while wrapping parser failures ([799b130](https://github.com/im-anishraj/arnio/commit/799b13049942a0f094525380d381a225fa9a5879))
* preserve empty pandas int64 dtype in from_pandas ([#2492](https://github.com/im-anishraj/arnio/issues/2492)) ([fce4203](https://github.com/im-anishraj/arnio/commit/fce4203904bb1a5e2c32b1cda76a8ee6c8982ad0))
* preserve Float64 nullable dtype in from_pandas round-trip ([#1984](https://github.com/im-anishraj/arnio/issues/1984)) ([5e2aa95](https://github.com/im-anishraj/arnio/commit/5e2aa95f958c546a0ee0598c884b122cbcd5c3a9))
* preserve row count for zero-column frames in drop_duplicates ([#2177](https://github.com/im-anishraj/arnio/issues/2177)) ([d32a292](https://github.com/im-anishraj/arnio/commit/d32a2921c865b2b709fac4e3cbaaa1968a8cfc4a))
* preserve row count in normalize_unicode for zero-column frames (… ([#2006](https://github.com/im-anishraj/arnio/issues/2006)) ([6973603](https://github.com/im-anishraj/arnio/commit/6973603d37b2308fc094dedbfe0f72033e758ebb))
* preserve word boundaries when redacting excluded columns ([#2519](https://github.com/im-anishraj/arnio/issues/2519)) ([645844c](https://github.com/im-anishraj/arnio/commit/645844c02dc179309dd15db5b723c16bcbd859cb))
* prevent benchmark scripts from deleting user files ([#2021](https://github.com/im-anishraj/arnio/issues/2021)) ([38f19ff](https://github.com/im-anishraj/arnio/commit/38f19ff774549d1cb263cee24e628449fc0f7cc6))
* prevent float64 suggestions for non-finite numeric strings ([10e5216](https://github.com/im-anishraj/arnio/commit/10e5216bb2e5bd908cd0d51da74f933942650889))
* prevent invalid column references after add_column ([#2549](https://github.com/im-anishraj/arnio/issues/2549)) ([20c894c](https://github.com/im-anishraj/arnio/commit/20c894c398e20a3e4c1b0162ffa21f630a565ab4))
* **quality:** validate quality gate result constructors ([#2041](https://github.com/im-anishraj/arnio/issues/2041)) ([a8ecdc2](https://github.com/im-anishraj/arnio/commit/a8ecdc23d3c27fe4a0c819c86dd6fd6901463597))
* raise ValueError for empty columns in ArFrame.from_records with dict records ([#2125](https://github.com/im-anishraj/arnio/issues/2125)) ([b64e335](https://github.com/im-anishraj/arnio/commit/b64e3354789043ab8949947d9f823851c0669c46))
* reject duplicate subset columns ([78f001f](https://github.com/im-anishraj/arnio/commit/78f001f8bd056640d8d106cf08ec69880402c78c))
* reject empty subset in fill_nullsfix: reject empty subset in fill_nulls ([#2103](https://github.com/im-anishraj/arnio/issues/2103)) ([fd2f0fb](https://github.com/im-anishraj/arnio/commit/fd2f0fb6b2cab7d8c4330b0b44b2777926546aa3))
* reject impossible numeric Field bounds ([58abccc](https://github.com/im-anishraj/arnio/commit/58abcccd4deacab73165a028fed0ec7494f8c9a4))
* reject invalid tokens for forced numeric CSV dtypes ([#1980](https://github.com/im-anishraj/arnio/issues/1980)) ([169e5a2](https://github.com/im-anishraj/arnio/commit/169e5a2ef59bab018cfae2caf4129a8474499259))
* reject NaN/Infinity/-Infinity in read_jsonl with JsonlReadError line context ([#2150](https://github.com/im-anishraj/arnio/issues/2150)) ([9c284b4](https://github.com/im-anishraj/arnio/commit/9c284b4657a5fb2412a9f5cbe66f27f2e4f5f96b)), closes [#1943](https://github.com/im-anishraj/arnio/issues/1943)
* reject non-finite bounds in Int64 and Float64 ([#2120](https://github.com/im-anishraj/arnio/issues/2120)) ([1272625](https://github.com/im-anishraj/arnio/commit/1272625809378f609e0aa5c6c9331347604609a9))
* reject unknown keys in schema json payloads ([#2106](https://github.com/im-anishraj/arnio/issues/2106)) ([a7bae81](https://github.com/im-anishraj/arnio/commit/a7bae817769539845496335dfa337e4a8a8e0426))
* reject unsafe regex patterns in schema validation ([4607239](https://github.com/im-anishraj/arnio/commit/46072394bfb9bc9bda314bd9842a3748449bb08d))
* reject unsafe regex patterns in schema validation ([#2299](https://github.com/im-anishraj/arnio/issues/2299)) ([e055a37](https://github.com/im-anishraj/arnio/commit/e055a37472388c404f72cad683db048c999a3d94))
* reject unsupported object scalars in from_pandas ([#1903](https://github.com/im-anishraj/arnio/issues/1903)) ([#1983](https://github.com/im-anishraj/arnio/issues/1983)) ([e5d5e6c](https://github.com/im-anishraj/arnio/commit/e5d5e6cc86547f76236b89d09ca785c93c9a8eaf))
* reject whitespace-only names in register_validator ([#2123](https://github.com/im-anishraj/arnio/issues/2123)) ([159b6a4](https://github.com/im-anishraj/arnio/commit/159b6a46166483695549ef86892a8fdfe3d295d6))
* reject zero-column Parquet export that drops row count ([#2007](https://github.com/im-anishraj/arnio/issues/2007)) ([8c470ea](https://github.com/im-anishraj/arnio/commit/8c470ea825af935486efce9ea8fd29126006c2e9))
* remove invalid Frame constructor arguments in cleaning.cpp ([#2285](https://github.com/im-anishraj/arnio/issues/2285)) ([e9c9271](https://github.com/im-anishraj/arnio/commit/e9c9271abc71455265ddebc00b8151e29ba3d310))
* remove redundant pyarrow import that bypasses error handling ([bdff6e5](https://github.com/im-anishraj/arnio/commit/bdff6e57cc11a996d00ef06351cb8b9bbd98ff81))
* remove stale native extension artifacts in make clean ([#2109](https://github.com/im-anishraj/arnio/issues/2109)) ([ac52735](https://github.com/im-anishraj/arnio/commit/ac5273566d637d318c2172cc85b9928c65896df6))
* remove unused encoding arg and add to_csv to api docs ([32c82ec](https://github.com/im-anishraj/arnio/commit/32c82ec20e70ffba48088e53fad340878154557d))
* render zero-column ArFrame strings clearly ([2070b39](https://github.com/im-anishraj/arnio/commit/2070b3925aca203c3699f8b666a5edb002fcfc91))
* replace exception wording on 404 page with user-friendly copy ([#2356](https://github.com/im-anishraj/arnio/issues/2356)) ([#2493](https://github.com/im-anishraj/arnio/issues/2493)) ([b8f3605](https://github.com/im-anishraj/arnio/commit/b8f3605b350c1546820aef948a2c0d610ca8deaa))
* require auto_clean cast confirmation ([#2093](https://github.com/im-anishraj/arnio/issues/2093)) ([9cbc1a7](https://github.com/im-anishraj/arnio/commit/9cbc1a77f4848123d9564cf1d7c172132c779bae))
* resolve __version__ from pyproject.toml in source checkouts ([#2217](https://github.com/im-anishraj/arnio/issues/2217)) ([78547ca](https://github.com/im-anishraj/arnio/commit/78547ca043f6e058e5dddd2b3d51b4e59b6ded8f))
* respect encoding in delimiter sniffing ([83310cb](https://github.com/im-anishraj/arnio/commit/83310cb3b7ff490ec3b3ad8d60527e6dc7541e2c))
* restore benchmark summary script entrypoint ([39837d4](https://github.com/im-anishraj/arnio/commit/39837d47a5f1ee01bbfe0647581b9a5f2e18eb53))
* restore public exports and main CI ([#2499](https://github.com/im-anishraj/arnio/issues/2499)) ([5e07c93](https://github.com/im-anishraj/arnio/commit/5e07c9329963a04fbf43907c2d9166144ac30df2))
* restrict write_csv line_terminator to standard newline values ([#2004](https://github.com/im-anishraj/arnio/issues/2004)) ([017d8d4](https://github.com/im-anishraj/arnio/commit/017d8d4ae2a3c839580a1d82a862e637dea12375))
* return fresh object for zero-row drop_constant_columns ([#2026](https://github.com/im-anishraj/arnio/issues/2026)) ([18ffc55](https://github.com/im-anishraj/arnio/commit/18ffc55f5f80b22ca90874f32d6c3fe358c1beb1))
* return zero-column ArFrame when select_dtypes matches no columns ([#1978](https://github.com/im-anishraj/arnio/issues/1978)) ([50d5bb3](https://github.com/im-anishraj/arnio/commit/50d5bb32be63b49af551061610cd35655e08677b))
* safe_divide_columns rejects existing output columns ([#592](https://github.com/im-anishraj/arnio/issues/592)) ([71a0923](https://github.com/im-anishraj/arnio/commit/71a0923f548565992205c70da7e5000e2bc9e735))
* safe_divide_columns rejects existing output columns ([#592](https://github.com/im-anishraj/arnio/issues/592)) ([7de58da](https://github.com/im-anishraj/arnio/commit/7de58da9e886af883f433ba247954e25553f5869))
* **schema:** include schema rules in diff_schema ([c7fa645](https://github.com/im-anishraj/arnio/commit/c7fa64590aa8eac15d09ee9c1e9db148156b7050))
* **schema:** normalize timestamps and arrays in validation exports ([d9fef17](https://github.com/im-anishraj/arnio/commit/d9fef177dbba75d0828f724bb8ff8993fd1f03f9))
* **schema:** preserve severity for unknown semantic issues ([9b1ef0f](https://github.com/im-anishraj/arnio/commit/9b1ef0f37baab5088f486b0d8d7a12549d1151c5))
* **schema:** reject bare strings in CurrencyCode allowed values ([ccd7b58](https://github.com/im-anishraj/arnio/commit/ccd7b5807a9e8298e39ac84630fad6aeaab42dea))
* **schema:** require explicit custom validator overwrite ([#2046](https://github.com/im-anishraj/arnio/issues/2046)) ([4dbdcc3](https://github.com/im-anishraj/arnio/commit/4dbdcc35277662ccee2bb4604c461326c39a7e7a))
* **schema:** validate core ValidationIssue fields ([53571de](https://github.com/im-anishraj/arnio/commit/53571deb3009aa7800a8c15c5ec1fc6aa6ff96dd))
* **schema:** validate schema_to_yaml output paths ([#2126](https://github.com/im-anishraj/arnio/issues/2126)) ([a881c77](https://github.com/im-anishraj/arnio/commit/a881c775a4e5d6ac9993d35f307962b9b5a3ab50))
* **schema:** validate ValidationResult constructor fields ([#2102](https://github.com/im-anishraj/arnio/issues/2102)) ([5ca9786](https://github.com/im-anishraj/arnio/commit/5ca978602b8a42f13a1e0d7b91d8bf81019961ae))
* set quality_score to 0.0 in profile_chunked (accuracy contract) ([cb17817](https://github.com/im-anishraj/arnio/commit/cb17817a20730119bed867623bd52cd0e5ba7e7f))
* simplify regression handling and apply black formatting ([e9e577d](https://github.com/im-anishraj/arnio/commit/e9e577ded64db669d8f7bc5de6e2dd3e1900ff3e))
* skip empty chunked CSV frames after bad-row filtering ([#1991](https://github.com/im-anishraj/arnio/issues/1991)) ([fb56f8b](https://github.com/im-anishraj/arnio/commit/fb56f8b44e17aafa95893d3b3cd982b55099fd69))
* skip empty chunked CSV frames after bad-row filtering ([#1991](https://github.com/im-anishraj/arnio/issues/1991)) ([#2016](https://github.com/im-anishraj/arnio/issues/2016)) ([7a85e0b](https://github.com/im-anishraj/arnio/commit/7a85e0be032afc9e42b24d88066d63271ff3a6bf))
* subprocess-validation-issue ([#2000](https://github.com/im-anishraj/arnio/issues/2000)) ([82e5077](https://github.com/im-anishraj/arnio/commit/82e507781089d40840924567c8b9a7af32d02a70))
* support cast_types ignore errors ([#2094](https://github.com/im-anishraj/arnio/issues/2094)) ([1534ceb](https://github.com/im-anishraj/arnio/commit/1534cebfcaddd74248bce939b06a4219dbfdcdb4))
* support non-ASCII write_csv output paths ([#2018](https://github.com/im-anishraj/arnio/issues/2018)) ([9681512](https://github.com/im-anishraj/arnio/commit/968151263121fff22b47e58e23697bdb7f13f087))
* sync rename_columns_matching with API docs ([8c2dac7](https://github.com/im-anishraj/arnio/commit/8c2dac728d006131fdc14eb3f8d78c3a5bb3469e))
* **types:** add select_rows to Frame native stub ([#1683](https://github.com/im-anishraj/arnio/issues/1683)) ([#1934](https://github.com/im-anishraj/arnio/issues/1934)) ([f356865](https://github.com/im-anishraj/arnio/commit/f35686589d156eec3910c2900b636b17d0414506))
* Update tests and remove unused imports ([5288320](https://github.com/im-anishraj/arnio/commit/5288320e2ef60691df692bd5ee90cb4b3ee1ee4e))
* use frame.clone() in ArFrame.__copy__ for mutation isolation ([#2242](https://github.com/im-anishraj/arnio/issues/2242)) ([bb74ab2](https://github.com/im-anishraj/arnio/commit/bb74ab2c6e76b464361149b10b9f81ea39eeb7d0))
* use locale-independent float parsing in cleaning ([0cfd04a](https://github.com/im-anishraj/arnio/commit/0cfd04aa3696a7c7dae9d0aabadb82a13b187a5e))
* validate and normalize structured metadata in schema_to_dict ([#1797](https://github.com/im-anishraj/arnio/issues/1797)) ([#2030](https://github.com/im-anishraj/arnio/issues/2030)) ([eedfafa](https://github.com/im-anishraj/arnio/commit/eedfafa96e260aa5f48921d5e209587d25cd4cc6))
* validate ArFrame astype dtype arguments ([24c7e20](https://github.com/im-anishraj/arnio/commit/24c7e20bb632b4291d5491f7c461ed19cfc2e7b2))
* validate ArnioCleaner set_params updates ([f575a00](https://github.com/im-anishraj/arnio/commit/f575a00239fe4698c02da8950cb45358ff5e2043))
* validate auto_clean mode before membership check ([#2270](https://github.com/im-anishraj/arnio/issues/2270)) ([b8d4261](https://github.com/im-anishraj/arnio/commit/b8d4261d35b4e12b29d42af0d7e8a8c50c0b146d))
* validate Custom validator names before registry lookup ([#2043](https://github.com/im-anishraj/arnio/issues/2043)) ([305bccd](https://github.com/im-anishraj/arnio/commit/305bccd2ed041992a38948af796a51420a3ed47c))
* validate empty HTML report output paths ([1e5fda0](https://github.com/im-anishraj/arnio/commit/1e5fda051cad2d58a494290a3128e71e4fe70a9d))
* validate field dtype values ([#2245](https://github.com/im-anishraj/arnio/issues/2245)) ([3640b73](https://github.com/im-anishraj/arnio/commit/3640b7347033b38e393268e283037a67215e9c41))
* validate filter_rows column and op argument types ([7b13122](https://github.com/im-anishraj/arnio/commit/7b13122dffb20c828d49345fe73071cedcad2978))
* validate frame inputs in CSV and Parquet writers ([#2037](https://github.com/im-anishraj/arnio/issues/2037)) ([8a43300](https://github.com/im-anishraj/arnio/commit/8a433004413a7b1fc3ed7f7f45cc1862ba4c02e1)), closes [#1408](https://github.com/im-anishraj/arnio/issues/1408)
* validate importable arnio core in check_env ([#2389](https://github.com/im-anishraj/arnio/issues/2389)) ([7f3ab1d](https://github.com/im-anishraj/arnio/commit/7f3ab1debe3c8bfec6ed4881cf0c1c8faaf6a4a9))
* validate input_features in ArnioCleaner.get_feature_names_out ([#1994](https://github.com/im-anishraj/arnio/issues/1994)) ([475f8d1](https://github.com/im-anishraj/arnio/commit/475f8d1bb302dbc138849dcceb6027d851be272b))
* validate normalize_whitespace columns input ([#1522](https://github.com/im-anishraj/arnio/issues/1522)) ([1fd11c5](https://github.com/im-anishraj/arnio/commit/1fd11c54b3d931ea89d651f218cd99f3414f352e))
* validate orient type in ArFrame.to_dict ([#2511](https://github.com/im-anishraj/arnio/issues/2511)) ([7b2ed5a](https://github.com/im-anishraj/arnio/commit/7b2ed5a4fec3f146258d296d2b6ba39b8e5c7ac9))
* validate parse_bool_strings token container types ([#2015](https://github.com/im-anishraj/arnio/issues/2015)) ([cf33bbd](https://github.com/im-anishraj/arnio/commit/cf33bbdae70d179d4c2c5b7dbdfd31ab7e4858ac))
* validate pipeline registry inputs before state mutation ([#1849](https://github.com/im-anishraj/arnio/issues/1849)) ([4cbe53f](https://github.com/im-anishraj/arnio/commit/4cbe53f3abeb27154c4a164edfe2fd3e3fa4e7fe))
* validate pipeline step container before step iteration ([#2248](https://github.com/im-anishraj/arnio/issues/2248)) ([13c3c08](https://github.com/im-anishraj/arnio/commit/13c3c0890c1c5801851f1291feec7d9c8fca4381)), closes [#1656](https://github.com/im-anishraj/arnio/issues/1656)
* validate ProfileComparison status_counts values ([#2005](https://github.com/im-anishraj/arnio/issues/2005)) ([caa4963](https://github.com/im-anishraj/arnio/commit/caa4963bf7b7ffb4c69ec44148e5de004add4449))
* validate quality report dataclass invariants ([1d9ab8a](https://github.com/im-anishraj/arnio/commit/1d9ab8a594c51fdcdb96a05a360fce1c54103bdd))
* validate read_jsonl_chunked path type ([#2479](https://github.com/im-anishraj/arnio/issues/2479)) ([b58ee35](https://github.com/im-anishraj/arnio/commit/b58ee35e677ab03140700164b4008a08562e2f26))
* validate required_if scalar values ([32a819a](https://github.com/im-anishraj/arnio/commit/32a819a34179f3653b29b837f7d2c7fc27bd6941))
* validate safe_divide_columns fill_value ([#1850](https://github.com/im-anishraj/arnio/issues/1850)) ([2f5f9bc](https://github.com/im-anishraj/arnio/commit/2f5f9bcb46af994ee6ac6fadf91c1ac6215accc9))
* validate schema export field names ([0c5c47a](https://github.com/im-anishraj/arnio/commit/0c5c47aa9d46be8d73d6cef8af8f1cb4f626dbad))
* validate schema severity type ([22b0059](https://github.com/im-anishraj/arnio/commit/22b005988c2625d50bbfd687351b5ace739338e3))
* validate SchemaDiff and SchemaDiffEntry inputs ([#2386](https://github.com/im-anishraj/arnio/issues/2386)) ([ad99c5a](https://github.com/im-anishraj/arnio/commit/ad99c5ab3557719a11daca3f7ec6208e69473ddd))
* validate slugify_column_names input frame ([bef655c](https://github.com/im-anishraj/arnio/commit/bef655c2f9cb396abb523e93fc1e453c93e50b70))
* validate steps argument in ArnioCleaner.__init__ and fit ([#2101](https://github.com/im-anishraj/arnio/issues/2101)) ([974a039](https://github.com/im-anishraj/arnio/commit/974a039a0efa1ce949994943a692c81147d544b8))
* validate winsorize bounds before comparisons ([#2518](https://github.com/im-anishraj/arnio/issues/2518)) ([bdeac9b](https://github.com/im-anishraj/arnio/commit/bdeac9b2d89f5a32db12f2ef2ac71a7e2d14c82b))
* validate write_parquet preserve_attrs type ([#2480](https://github.com/im-anishraj/arnio/issues/2480)) ([598cefa](https://github.com/im-anishraj/arnio/commit/598cefa65dc80fae4dcd5df3b79d006fbcfe20fc))
* validate writer output path before suffix checks ([50feb05](https://github.com/im-anishraj/arnio/commit/50feb05ef94fdf26181bbad2197329ba7df5afeb))
* **website:** fix code highlighter corrupting copied Python snippets ([b7ce226](https://github.com/im-anishraj/arnio/commit/b7ce226ab18533613ff233a4d65336b2e0c99a7f))
* **website:** fix code highlighter corrupting copied Python snippets ([0820dcb](https://github.com/im-anishraj/arnio/commit/0820dcb79af9fd8e3f8b547628e7e1b4909f22fa)), closes [#2154](https://github.com/im-anishraj/arnio/issues/2154)
* **website:** handle unavailable localStorage in theme script ([#2237](https://github.com/im-anishraj/arnio/issues/2237)) ([ce7b495](https://github.com/im-anishraj/arnio/commit/ce7b495e7a0bb36c5fe2d61436424827f51640f4))
* **website:** link mobile menu toggle to navigation ([474a7c6](https://github.com/im-anishraj/arnio/commit/474a7c62f2238931af65655991b37a71d0d0594f))
* **website:** link mobile menu toggle to navigation ([bcdfb36](https://github.com/im-anishraj/arnio/commit/bcdfb365b87ed21da312fe98ea32224acb4107bc))


### Performance Improvements

* defer non-critical JS and lazy load footer images ([36aef98](https://github.com/im-anishraj/arnio/commit/36aef98ab6ff22fb0e809257c4255b0343493604)), closes [#2054](https://github.com/im-anishraj/arnio/issues/2054)
* optimize Frame::describe() direct storage access ([#2523](https://github.com/im-anishraj/arnio/issues/2523)) ([79e759f](https://github.com/im-anishraj/arnio/commit/79e759f8f9acb4bc535711d1e28bb8578e26ffe7))
* pre-allocate Column vectors in from_dict when row_count is known ([#2418](https://github.com/im-anishraj/arnio/issues/2418)) ([e5a1367](https://github.com/im-anishraj/arnio/commit/e5a1367c438409fe048250a02daa52fe49eec86e))
* **schema:** reduce ValidationIssue creation overhead in Schema.validate ([#2433](https://github.com/im-anishraj/arnio/issues/2433)) ([4ccae17](https://github.com/im-anishraj/arnio/commit/4ccae179b093289f30b04555838b3c777269c6f8))
* skip csv inference for fully explicit dtypes ([#1910](https://github.com/im-anishraj/arnio/issues/1910)) ([5d1f66b](https://github.com/im-anishraj/arnio/commit/5d1f66b04314e0b94fb3311ffd02212202a0dba0))
* vectorize date semantic validation ([4136bb8](https://github.com/im-anishraj/arnio/commit/4136bb85f9efcbd784ca9ebde708d6f8bea5ae6f))
* vectorize date semantic validation ([a37adae](https://github.com/im-anishraj/arnio/commit/a37adaeb87f9c8e22c197014b1c6860bf6470d14))


### Documentation

* add auto_clean dry-run and explain workflow examples ([db6a571](https://github.com/im-anishraj/arnio/commit/db6a571ba324cb21d1e24267bb260ff9510b6e98))
* add auto_clean dry-run and explain workflow examples ([1c60a59](https://github.com/im-anishraj/arnio/commit/1c60a5978b3d4a6fdfe1ca9d9b28e862822e4dee))
* add chunked_workflows.md covering streaming validation and pipe… ([250377f](https://github.com/im-anishraj/arnio/commit/250377f1cf55aa2e161a515cfd1c605af9f5baf0))
* add chunked_workflows.md covering streaming validation and pipeline behavior ([e839675](https://github.com/im-anishraj/arnio/commit/e8396752703a851c6e74ade023c7036d56e2ecb2))
* add chunked_workflows.md covering streaming validation and pipeline behavior ([16b0524](https://github.com/im-anishraj/arnio/commit/16b0524934e3bcb45b9e7f24ae08ece467cc241c))
* add cross-domain data drift and profile comparison tutorial ([#2147](https://github.com/im-anishraj/arnio/issues/2147)) ([37365da](https://github.com/im-anishraj/arnio/commit/37365da5f2b743f089593612e38f6ecab61710f5))
* add encoding_errors to read_jsonl docstring and smoke parity check ([#2494](https://github.com/im-anishraj/arnio/issues/2494)) ([e42d500](https://github.com/im-anishraj/arnio/commit/e42d500dba5ebe09812869dd2737504cec404087))
* add interactive Jupyter notebooks with Colab badges (fixes [#2058](https://github.com/im-anishraj/arnio/issues/2058)) ([#2265](https://github.com/im-anishraj/arnio/issues/2265)) ([6fbaaf8](https://github.com/im-anishraj/arnio/commit/6fbaaf816352999444fb99ad60dd3376b540e417))
* add pandas accessor examples for suggest_cleaning, auto_clean, and validate ([#2183](https://github.com/im-anishraj/arnio/issues/2183)) ([c0d6aac](https://github.com/im-anishraj/arnio/commit/c0d6aaca072d958cb1d1db03bcbdb4185a221e0e))
* add parameterized pipeline step example in CONTRIBUTING.md ([#1576](https://github.com/im-anishraj/arnio/issues/1576)) ([e70ea85](https://github.com/im-anishraj/arnio/commit/e70ea85238f1366d5a6066f72e14e6bdfd7294af))
* add read_csv parser options note to website API entry ([c3a3416](https://github.com/im-anishraj/arnio/commit/c3a341658e5f641a1a0953ef5b3dc620841a01cc)), closes [#2155](https://github.com/im-anishraj/arnio/issues/2155)
* add read_csv_chunked parity note and confirm full signature ([0ee92bd](https://github.com/im-anishraj/arnio/commit/0ee92bdf470908212cc9f94da29961823adb7e79)), closes [#2156](https://github.com/im-anishraj/arnio/issues/2156)
* add scan_csv sampling example ([#2216](https://github.com/im-anishraj/arnio/issues/2216)) ([ab0bc56](https://github.com/im-anishraj/arnio/commit/ab0bc56b22611719609cbc3f2d43467d367903c2))
* add schema unique and cross-field rule examples ([3b2870b](https://github.com/im-anishraj/arnio/commit/3b2870b9ae1760121146f0690aea5bdbacf5da60)), closes [#2169](https://github.com/im-anishraj/arnio/issues/2169)
* add troubleshooting for missing hypothesis dependency ([#1733](https://github.com/im-anishraj/arnio/issues/1733)) ([432f01e](https://github.com/im-anishraj/arnio/commit/432f01e5ebf872628faf482bd5820996c525d554))
* Added the post assignment and reassignment rules. ([#1997](https://github.com/im-anishraj/arnio/issues/1997)) ([c373286](https://github.com/im-anishraj/arnio/commit/c373286bc29b42a8c168ea08581cab817750c072))
* align benchmark memory wording with current evidence ([#2243](https://github.com/im-anishraj/arnio/issues/2243)) ([5077280](https://github.com/im-anishraj/arnio/commit/5077280019376b68e78c662742a982ea43bb6f9c))
* align on_bad_lines examples with default value 'error' (fixes [#1979](https://github.com/im-anishraj/arnio/issues/1979)) ([#2266](https://github.com/im-anishraj/arnio/issues/2266)) ([e9917a0](https://github.com/im-anishraj/arnio/commit/e9917a00774fc6a06ede6c8fdb7d0c80335357c0))
* align README custom pipeline example with subset API ([#2268](https://github.com/im-anishraj/arnio/issues/2268)) ([16a2eff](https://github.com/im-anishraj/arnio/commit/16a2eff03e66848954e279236afbd2fac7c8c6c4))
* align website API reference exports ([940ba37](https://github.com/im-anishraj/arnio/commit/940ba372551c65962730d84826a4ee71f376f8c1))
* aligned the labels with the live labels ([#1946](https://github.com/im-anishraj/arnio/issues/1946)) ([ab91e50](https://github.com/im-anishraj/arnio/commit/ab91e50c29929e78be3311d77ad787507a0edbd7))
* **api:** document auto_clean safety options and return shapes ([b62d1fb](https://github.com/im-anishraj/arnio/commit/b62d1fbf3a4d9b94c4c0d499ed650caf8f202fe8))
* **api:** document auto_clean safety options and return shapes ([0da3869](https://github.com/im-anishraj/arnio/commit/0da3869ff6bb10bdfdedcb70a593a5c0e1428661))
* **api:** document DataQualityReport exporter signatures and options ([#2212](https://github.com/im-anishraj/arnio/issues/2212)) ([2138ef8](https://github.com/im-anishraj/arnio/commit/2138ef80232bea8f9378917f730a0d8e554e3ed8))
* badge website APIs by released vs current-main availability ([#2561](https://github.com/im-anishraj/arnio/issues/2561)) ([ab084a1](https://github.com/im-anishraj/arnio/commit/ab084a1bf393292f076ac30b935d812c5cfc720a))
* clarify duplicate header handling status ([42ea3e4](https://github.com/im-anishraj/arnio/commit/42ea3e4274abbcf4bd628b290c31d09f7138673e))
* clarify sniff_delimiter sample_size is character-count, not byte-count ([#1958](https://github.com/im-anishraj/arnio/issues/1958)) ([8660eed](https://github.com/im-anishraj/arnio/commit/8660eed34ddaeb2834ba76383678b420b17ce218)), closes [#1944](https://github.com/im-anishraj/arnio/issues/1944)
* document additional ArFrame helper methods ([b54e782](https://github.com/im-anishraj/arnio/commit/b54e7826cb7020fc893c3ef2dcc1e33ec1635498))
* document additional ArFrame helper methods ([8ad20ca](https://github.com/im-anishraj/arnio/commit/8ad20ca74e68b12a575c7bc581c91b831e39d5e9))
* document df.arnio.clean() in website API reference ([#2223](https://github.com/im-anishraj/arnio/issues/2223)) ([c9f5829](https://github.com/im-anishraj/arnio/commit/c9f58297104e1f623302c8cfe9d767e0b7d77219))
* document notebook HTML representations for ArFrame and DataQualityReport ([#2185](https://github.com/im-anishraj/arnio/issues/2185)) ([23d2eb2](https://github.com/im-anishraj/arnio/commit/23d2eb2b13f24a4e1496a0b3ea2ffd376126973e))
* document quality gate thresholds ([ffdaac4](https://github.com/im-anishraj/arnio/commit/ffdaac49d198932e4faa6879346528246c3afab3))
* document quality gate thresholds ([473de95](https://github.com/im-anishraj/arnio/commit/473de955b4fb62e53df495746cb5d08658e3b6ce))
* document Schema unique and rules options ([#2186](https://github.com/im-anishraj/arnio/issues/2186)) ([09a8654](https://github.com/im-anishraj/arnio/commit/09a8654139a5bba922ed947ceed18d24d4b57a84))
* document sniff_delimiter sample_size parameter ([#2206](https://github.com/im-anishraj/arnio/issues/2206)) ([933902a](https://github.com/im-anishraj/arnio/commit/933902a79ab6854aaff77fd83963166d50ef0fc3)), closes [#2160](https://github.com/im-anishraj/arnio/issues/2160)
* document write_parquet preserve_attrs and compression options ([#2208](https://github.com/im-anishraj/arnio/issues/2208)) ([d6574b6](https://github.com/im-anishraj/arnio/commit/d6574b6ec803ab561c9fc34baa6c4755b8bf6f1a)), closes [#2159](https://github.com/im-anishraj/arnio/issues/2159)
* **examples:** use clip_numeric in NumPy example ([#2045](https://github.com/im-anishraj/arnio/issues/2045)) ([1640f5c](https://github.com/im-anishraj/arnio/commit/1640f5cce19b67b68fc3c76ede4523c5fa521e61))
* expand CSV guide option table ([#2247](https://github.com/im-anishraj/arnio/issues/2247)) ([7e15050](https://github.com/im-anishraj/arnio/commit/7e150508878c6ea26f66f5dc14fe22237cd90987))
* expand field builder parameter details ([#2190](https://github.com/im-anishraj/arnio/issues/2190)) ([fe4e21d](https://github.com/im-anishraj/arnio/commit/fe4e21ddcc6d89e9a1341fb686e5232ea80a7397))
* expand pandas accessor integration guide ([#2496](https://github.com/im-anishraj/arnio/issues/2496)) ([23f6e55](https://github.com/im-anishraj/arnio/commit/23f6e55f2ff55866303af3ecd7e4320e16febc3c))
* fix auto_clean dry-run and explain workflow examples ([63ae9f6](https://github.com/im-anishraj/arnio/commit/63ae9f65718c719d7bf7e02e22bfc6560bff5a60))
* fix label name mismatches in ISSUE_TRIAGE.md ([#2127](https://github.com/im-anishraj/arnio/issues/2127)) ([5b79cf0](https://github.com/im-anishraj/arnio/commit/5b79cf0f367b2d8372bd8b033439078afb07d69a))
* fix quality reports exclusion example ([87e3345](https://github.com/im-anishraj/arnio/commit/87e3345742465819633b07dc6c24524abdde98eb))
* fix read_csv_chunked API signature (chunksize, drop encoding_errors, add missing params) ([954c1cd](https://github.com/im-anishraj/arnio/commit/954c1cd8007b884ce576c0787b0b3c1ba79e26f1))
* improve Quickstart onboarding guidance ([#741](https://github.com/im-anishraj/arnio/issues/741)) ([970d833](https://github.com/im-anishraj/arnio/commit/970d8333011a924a9f34b49146b86cb3797a28f4))
* refresh roadmap status text ([#1961](https://github.com/im-anishraj/arnio/issues/1961)) ([63c9ba9](https://github.com/im-anishraj/arnio/commit/63c9ba9933384efb6c8d917ef7b27b0d56ea03b0))
* remove corrupted separators from API reference ([#1829](https://github.com/im-anishraj/arnio/issues/1829)) ([5233d5e](https://github.com/im-anishraj/arnio/commit/5233d5e50dd1dc678d3fc35cd5dc24edd8b2b7e8))
* remove duplicate comment in auto_clean example ([64809a1](https://github.com/im-anishraj/arnio/commit/64809a1d41a8bc14ace1d7de0278e69bcc7bd6a8))
* Update README with current active URL ([e2f47d2](https://github.com/im-anishraj/arnio/commit/e2f47d271ea6eb2546aab828130e3e2ac5490e8f))
* update website latest release references to v1.19.0 ([addde49](https://github.com/im-anishraj/arnio/commit/addde49f620427de1967329a20f88e165351994d)), closes [#2115](https://github.com/im-anishraj/arnio/issues/2115)
* update website read_jsonl signature for encoding options ([#2218](https://github.com/im-anishraj/arnio/issues/2218)) ([adc9b1b](https://github.com/im-anishraj/arnio/commit/adc9b1bc477ff860f4b1f428eeb1a3832097b573))
* **website:** document CI checks for contributors ([#2222](https://github.com/im-anishraj/arnio/issues/2222)) ([0a765fb](https://github.com/im-anishraj/arnio/commit/0a765fb95e58973fd8e1438dd0b2d80dda836d35))

## [1.19.0](https://github.com/im-anishraj/arnio/compare/v1.18.0...v1.19.0) (2026-05-29)


### Features

* add `ArFrame.from_pandas()` convenience constructor
* add custom pipeline step unregister support
* add `clean_column_names`, `normalize_whitespace`, and richer schema summary helpers
* add schema validation improvements, including custom-field `required_if`, case-insensitive allowed strings, `LanguageCode`, and `TimeZone`
* add data quality export helpers and richer quality summaries


### Bug Fixes

* harden CSV, JSONL, schema, cleaning, and pipeline input validation
* reject unsafe read/write delimiters and nested JSONL values with clearer errors
* improve optional Arrow/parquet release-test coverage

## [1.18.0](https://github.com/im-anishraj/arnio/compare/v1.17.1...v1.18.0) (2026-05-22)


### Features

* add Arrow export API and bool dtype detection ([9064b48](https://github.com/im-anishraj/arnio/commit/9064b486ef8fbb4a3398d45719c715f820fe5a24))
* **schema:** add max_errors support to schema validation ([dd025c1](https://github.com/im-anishraj/arnio/commit/dd025c10739e0477a312fec6b1a00586d76dbe61))


### Bug Fixes

* **cleaning:** include received type in mapping validation errors ([2c79c49](https://github.com/im-anishraj/arnio/commit/2c79c490214a6e36610e633f0f547251f86cef26)), closes [#581](https://github.com/im-anishraj/arnio/issues/581)

## [1.17.1](https://github.com/im-anishraj/arnio/compare/v1.17.0...v1.17.1) (2026-05-22)


### Documentation

* clarify chunked schema validation contract ([e570c38](https://github.com/im-anishraj/arnio/commit/e570c380f1062bfec8b43929b052c9c80e195c33))

## [1.17.0](https://github.com/im-anishraj/arnio/compare/v1.16.0...v1.17.0) (2026-05-22)


### Features

* add allowed_schemes parameter to URL field validation ([#997](https://github.com/im-anishraj/arnio/issues/997)) ([ff6ca13](https://github.com/im-anishraj/arnio/commit/ff6ca13f3514da5e29b13665e013d832a63e3f80))
* add ArFrame.from_records constructor ([#998](https://github.com/im-anishraj/arnio/issues/998)) ([c267733](https://github.com/im-anishraj/arnio/commit/c2677339eb85f1ce7aebcc6fc7c8ae7029398b23))
* add ArFrame.schema_summary property ([#224](https://github.com/im-anishraj/arnio/issues/224)) ([#1005](https://github.com/im-anishraj/arnio/issues/1005)) ([19e70b5](https://github.com/im-anishraj/arnio/commit/19e70b5e3d3f13c16343cfa62c9ccf44d80db376))
* add configurable bad-line handling for malformed row widths ([#1028](https://github.com/im-anishraj/arnio/issues/1028)) ([ae29e3a](https://github.com/im-anishraj/arnio/commit/ae29e3a7079aee97263862885ebe9209a4bbfa28))
* add drop_empty_columns step ([#146](https://github.com/im-anishraj/arnio/issues/146)) ([#984](https://github.com/im-anishraj/arnio/issues/984)) ([8aac4f5](https://github.com/im-anishraj/arnio/commit/8aac4f58bfc18e0c05be0dc04c362d38cb5185d0))
* add dtype support to read_csv ([#951](https://github.com/im-anishraj/arnio/issues/951)) ([c106eef](https://github.com/im-anishraj/arnio/commit/c106eef7aa882208890a232972ef569c9f7b0776))
* add DuckDB relation registration helper ([d5495a8](https://github.com/im-anishraj/arnio/commit/d5495a8ccbd36ce9499d38161c50cb87d6185b4a))
* add near-constant column detection to quality reports ([#919](https://github.com/im-anishraj/arnio/issues/919)) ([dcf8835](https://github.com/im-anishraj/arnio/commit/dcf8835054ea4cd98e8cd059feb42f64a6cba346)), closes [#177](https://github.com/im-anishraj/arnio/issues/177)
* add on_bad_lines implementations for read and next_chunk function ([eff753a](https://github.com/im-anishraj/arnio/commit/eff753a47f682c3b04ab8633917126751f693bbc))
* add opt-in pipeline context object ([#164](https://github.com/im-anishraj/arnio/issues/164)) ([#873](https://github.com/im-anishraj/arnio/issues/873)) ([79ad338](https://github.com/im-anishraj/arnio/commit/79ad338d5e7f26fcd1197e64e6c485686dc04efd))
* add schema YAML exporter (schema_to_dict, schema_to_yaml) ([#1014](https://github.com/im-anishraj/arnio/issues/1014)) ([cb1bdbe](https://github.com/im-anishraj/arnio/commit/cb1bdbe08ed61bee5e48f24843526fa2704ced23))
* add select_columns cleaning primitive ([612b533](https://github.com/im-anishraj/arnio/commit/612b5336f4d8a888fa0918837162c40f60fbb3bf))
* add skiprows parameter to read_csv ([8343e23](https://github.com/im-anishraj/arnio/commit/8343e23fa491ff69674399e48bd05f27b010ad7c))
* add to_dict() method to ArFrame ([#1023](https://github.com/im-anishraj/arnio/issues/1023)) ([986ac1c](https://github.com/im-anishraj/arnio/commit/986ac1ca8b9508f563d732f057c0b88e97bc5506))
* add winsorize_outliers cleaning step ([#1020](https://github.com/im-anishraj/arnio/issues/1020)) ([738d68e](https://github.com/im-anishraj/arnio/commit/738d68e2190f5934ead3bc6a8e53161112e602a8))
* **csv:** add encoding_errors support ([#990](https://github.com/im-anishraj/arnio/issues/990)) ([9e0eef0](https://github.com/im-anishraj/arnio/commit/9e0eef01eb2db71235b73464f3cab6da654357e8))
* implement ArFrame.describe for summary statistics ([#996](https://github.com/im-anishraj/arnio/issues/996)) ([f0ff312](https://github.com/im-anishraj/arnio/commit/f0ff31251fa3dda9c43ac86bd91227a2604ad17b))
* **io:** add write_parquet() via optional pyarrow extra ([14ddc30](https://github.com/im-anishraj/arnio/commit/14ddc3021929de6a47deb1a5f8a61c3a572cdcab))
* **pipeline:** add verbose diagnostics logging ([bf74d79](https://github.com/im-anishraj/arnio/commit/bf74d7909972bbd8ace9f37650ace8dd0fff7b9e))
* **quality:** add high-cardinality profile warnings ([d3f9ef0](https://github.com/im-anishraj/arnio/commit/d3f9ef088c554949053d54e87814338c9725e49f))
* **schema:** treat empty and whitespace strings as nulls ([7c90e3f](https://github.com/im-anishraj/arnio/commit/7c90e3fe7186656846b7de12e8e3116fee5955fd))
* support configurable csv decimal separators ([f84ad9b](https://github.com/im-anishraj/arnio/commit/f84ad9b936bf2d286c9c8713cadf9d428d52a864))
* **types:** add _arnio_cpp extension stubs ([47f0d3c](https://github.com/im-anishraj/arnio/commit/47f0d3c75ee4b60116c27792d16b02b00f3c267d))
* update Python interfaces ([5be905d](https://github.com/im-anishraj/arnio/commit/5be905d93440e8e9726b40ec12620e2d8f86c7a7))


### Bug Fixes

* centralize rename_columns validation ([#994](https://github.com/im-anishraj/arnio/issues/994)) ([d36f7af](https://github.com/im-anishraj/arnio/commit/d36f7af93bc3d0a9f390961fe120df23c4e57088))
* **cleaning:** safe_divide_columns now catches string zero denominators ([#1021](https://github.com/im-anishraj/arnio/issues/1021)) ([fb717dd](https://github.com/im-anishraj/arnio/commit/fb717dd57c257d4a5f98527737c5172420c8afa3)), closes [#591](https://github.com/im-anishraj/arnio/issues/591)
* **csv_reader:** include line number in unterminated quoted field error ([#1008](https://github.com/im-anishraj/arnio/issues/1008)) ([f242ba6](https://github.com/im-anishraj/arnio/commit/f242ba6597cf54aed5d8f007e63dfa2305127031)), closes [#113](https://github.com/im-anishraj/arnio/issues/113)
* EOF bad row not counted as read ([486d8ef](https://github.com/im-anishraj/arnio/commit/486d8efc8375f5dceb129d5a0ef5f5de54ae3169))
* escape newlines in quality markdown cells ([c914778](https://github.com/im-anishraj/arnio/commit/c914778b1e1506952fdb272d0f052884910669aa))
* **frame:** add size and duplicate-name guards to add_column ([#937](https://github.com/im-anishraj/arnio/issues/937)) ([aad33d7](https://github.com/im-anishraj/arnio/commit/aad33d72787f883b4e4a42e5d157d5b05cee9074)), closes [#925](https://github.com/im-anishraj/arnio/issues/925)
* **frame:** prevent adding columns with duplicate names ([#988](https://github.com/im-anishraj/arnio/issues/988)) ([cf327dd](https://github.com/im-anishraj/arnio/commit/cf327dd296a8aef983e0ba7fad0020ea644d84f4))
* improve CSV permission error messages ([#989](https://github.com/im-anishraj/arnio/issues/989)) ([058d38b](https://github.com/im-anishraj/arnio/commit/058d38b77cece65d76762787315234cf8626bf8a))
* improve numeric string compatibility messaging ([4cea32d](https://github.com/im-anishraj/arnio/commit/4cea32d7d6037bdb0aef51c140d93c952843e05f))
* locale-independent CSV type inference and integer overflow handling ([a4a1f94](https://github.com/im-anishraj/arnio/commit/a4a1f947c999117be0200a9247fd4c2c8057397d))
* make clean target cross-platform safe for Windows ([973cfb1](https://github.com/im-anishraj/arnio/commit/973cfb179af5a0f08e4153a1023a1da76b6a184a))
* optimize strip_whitespace with in-place string mutation ([#978](https://github.com/im-anishraj/arnio/issues/978)) ([46db62c](https://github.com/im-anishraj/arnio/commit/46db62ce853c0487be7b279f0a4cdadb7da53607))
* Path.write_text performs differently on Windows ([1f7ec6b](https://github.com/im-anishraj/arnio/commit/1f7ec6bafe16913c23cc4dbda0525492ca13e212))
* preserve zero-column frame row count ([9b2f6df](https://github.com/im-anishraj/arnio/commit/9b2f6df782ffb2147fed365a036f45c11f78a40a))
* prevent drop_duplicates row-key collisions ([4481cd1](https://github.com/im-anishraj/arnio/commit/4481cd13bb44bd3e99a92cd62ec521056d72188d))
* reject empty subset for duplicate/null drops ([513bd71](https://github.com/im-anishraj/arnio/commit/513bd718c8276d041f09df4b484db849d639e710))
* reject extra CSV fields ([9908349](https://github.com/im-anishraj/arnio/commit/9908349233e596eec765d3721a8d8bf3e3d45dd9))
* relax CSV extension handling and infer TSV delimiter ([cc4423f](https://github.com/im-anishraj/arnio/commit/cc4423fa5f65755e707256592e63e408ecfbc818))
* resolve pipeline shorthand ambiguity for columns named mapping ([#993](https://github.com/im-anishraj/arnio/issues/993)) ([e8e0f9c](https://github.com/im-anishraj/arnio/commit/e8e0f9c5bac39b11c5514059cf45808baaafeab6))
* stop read_jsonl before parsing beyond nrows ([209dd18](https://github.com/im-anishraj/arnio/commit/209dd18d7c0097ee27213eff7c0fa108815091fb))
* support Unicode file paths in read_csv, scan_csv and chunked reads ([#955](https://github.com/im-anishraj/arnio/issues/955)) ([756a61b](https://github.com/im-anishraj/arnio/commit/756a61bd22fdd25f24d2337a64f7de48018ce630))
* validate boolean CSV options ([b0ce532](https://github.com/im-anishraj/arnio/commit/b0ce532bdce2cb56b62884dc3f93d47fc4adbfaa))


### Performance Improvements

* add sparse-null benchmark coverage ([6e7664c](https://github.com/im-anishraj/arnio/commit/6e7664c00464eef3336fda2957b21e5554000c1f))
* **csv:** optimize parser I/O and field allocations ([2d83714](https://github.com/im-anishraj/arnio/commit/2d83714b664137a0dd4f2ab3a9ec5aa6eb90e5be))
* move unmodified columns in strip_whitespace and normalize_case ([6ed46f4](https://github.com/im-anishraj/arnio/commit/6ed46f46001511f8d65908ba2e4f9e35ea6947dd))
* replace integer parsing with from_chars ([3de01ba](https://github.com/im-anishraj/arnio/commit/3de01ba17ccc3a8c9961f913a2cb0c2e32d97654))


### Documentation

* add optimized light/dark theme logos ([#981](https://github.com/im-anishraj/arnio/issues/981)) ([35c679c](https://github.com/im-anishraj/arnio/commit/35c679c232374dc687b1a6d2e9e8a4e4b299b557))
* add schema validation tutorial example ([ede51a7](https://github.com/im-anishraj/arnio/commit/ede51a7e1b5bcc6d85a97ba6e6e2ec0c4c410594))
* add Windows build troubleshooting notes ([9317700](https://github.com/im-anishraj/arnio/commit/9317700c1d3fceeeb510997c486f2f6c9d5f6929))

## [1.16.0](https://github.com/im-anishraj/arnio/compare/v1.15.0...v1.16.0) (2026-05-20)


### Features

* warn on deprecated pipeline step aliases ([#853](https://github.com/im-anishraj/arnio/issues/853)) ([09bdb72](https://github.com/im-anishraj/arnio/commit/09bdb72a547856beb309bc1c93e1a0e0555f99d9))


### Performance Improvements

* **frame:** implement native select_columns path ([#917](https://github.com/im-anishraj/arnio/issues/917)) ([c9b6ba3](https://github.com/im-anishraj/arnio/commit/c9b6ba365e5e9e9832f2f4d39d4a4b4bac794a33))

## [1.15.0](https://github.com/im-anishraj/arnio/compare/v1.14.0...v1.15.0) (2026-05-20)


### Features

* add __getitem__ to ArFrame for column access ([78dd66c](https://github.com/im-anishraj/arnio/commit/78dd66c1053f6c04bc61c35a9b81f016b37ac73a))
* add ArFrame __contains__ support ([2e63c39](https://github.com/im-anishraj/arnio/commit/2e63c396730caef6e6b2d8d238c046ea22d889bc))
* add chunked CSV reading example ([58de14e](https://github.com/im-anishraj/arnio/commit/58de14e79e86d4bb7bcb557b93bdcf08f4baa91f))
* add conditional required validation ([34c75a2](https://github.com/im-anishraj/arnio/commit/34c75a20efb0e06acc2d036296e25eb484b090df))
* add confidence metadata to cleaning suggestions ([2a78f8a](https://github.com/im-anishraj/arnio/commit/2a78f8a09d36147ce58f554a153340a60cb888fd))
* add CSV delimiter sniffing helper (fixes [#127](https://github.com/im-anishraj/arnio/issues/127)) ([#801](https://github.com/im-anishraj/arnio/issues/801)) ([cad39d9](https://github.com/im-anishraj/arnio/commit/cad39d94501e6684dc364c246ffa9f867604bce6))
* add CurrencyCode schema validation ([fdfda2b](https://github.com/im-anishraj/arnio/commit/fdfda2b2774fcb3b45871314186ba84cf769b87d)), closes [#204](https://github.com/im-anishraj/arnio/issues/204)
* add DataQualityReport markdown export ([20b2f68](https://github.com/im-anishraj/arnio/commit/20b2f68c0fb29516366ca753327896a8eaba6392))
* add Date schema field ([c52ac18](https://github.com/im-anishraj/arnio/commit/c52ac18fff979ef5b49b04a00b8d6d8faa4b933d))
* add Decimal conversion policy ([97b1a1c](https://github.com/im-anishraj/arnio/commit/97b1a1cc0ede5fbf0aef4176339fa4b2cf4cfed0))
* add drop_columns cleaning primitive ([#769](https://github.com/im-anishraj/arnio/issues/769)) ([2616c66](https://github.com/im-anishraj/arnio/commit/2616c6691563c037cfbea0bffc140c5ed4ded05e))
* add drop_columns_matching cleaning step ([#743](https://github.com/im-anishraj/arnio/issues/743)) ([5db2fd1](https://github.com/im-anishraj/arnio/commit/5db2fd1ba8b040986eee08bc6fa27da1e5ccc473))
* add examples environment checker ([01b4c35](https://github.com/im-anishraj/arnio/commit/01b4c35081068ab68581de33b6705d2fc2da7fa6))
* add explain mode for auto_clean ([#692](https://github.com/im-anishraj/arnio/issues/692)) ([24036fa](https://github.com/im-anishraj/arnio/commit/24036fa259804ec504e36d2f94d5f4e4a3cac573))
* add head() and tail() methods to ArFrame ([#565](https://github.com/im-anishraj/arnio/issues/565)) ([f254add](https://github.com/im-anishraj/arnio/commit/f254add98cecb78404a99b01a9290fe96b2adb53))
* add numeric column histogram summaries ([#850](https://github.com/im-anishraj/arnio/issues/850)) ([85bdc36](https://github.com/im-anishraj/arnio/commit/85bdc36f37dd89023a18419d8bcb92ebbe1b2097))
* add numeric quantiles to profile reports ([3934520](https://github.com/im-anishraj/arnio/commit/3934520c61abc4fe038b973b8a999bb00520ba74))
* add optional pipeline timing metadata ([7da0bae](https://github.com/im-anishraj/arnio/commit/7da0bae28b0cd691781c47f572237dd629bfc2bc)), closes [#162](https://github.com/im-anishraj/arnio/issues/162)
* add PhoneNumber schema validator ([#745](https://github.com/im-anishraj/arnio/issues/745)) ([21717d0](https://github.com/im-anishraj/arnio/commit/21717d07e5bc03098809b1312d51b919c74fd123))
* add pipeline step registry introspection ([8178f0a](https://github.com/im-anishraj/arnio/commit/8178f0a995bc65f425189647ef4f8d59cf4e4537)), closes [#157](https://github.com/im-anishraj/arnio/issues/157)
* add quality score components ([130ad70](https://github.com/im-anishraj/arnio/commit/130ad70075757051f1a49c8a0d9d9efb7e5a94de))
* add reset_steps for pipeline registry cleanup ([71e3c09](https://github.com/im-anishraj/arnio/commit/71e3c09f87afe9db86215b52b129eb286be0461b))
* add sample_size to scan_csv ([9f72698](https://github.com/im-anishraj/arnio/commit/9f726987a08b57fc8fa5d6d611e59f6c444a6232))
* add schema JSON serialization ([7c919a1](https://github.com/im-anishraj/arnio/commit/7c919a1f48453b37975c1e964d72c90c1b86e6fc))
* add standardize_missing_tokens step ([b2bd596](https://github.com/im-anishraj/arnio/commit/b2bd596e03c5a3e3143093116ed7f58b557ef84b))
* add thousands separator parsing ([7ffe50c](https://github.com/im-anishraj/arnio/commit/7ffe50cfd669f96cbdc32248fd425d34eb9f1e83))
* add ValidationResult.raise_for_errors ([4c34bf6](https://github.com/im-anishraj/arnio/commit/4c34bf60f70fa2f5c3183a1598066c4f470003c1))
* add write_csv via C++ backend ([2a62edc](https://github.com/im-anishraj/arnio/commit/2a62edc94108f59fa4894ae88cf266000bb1626d))
* **csv:** add chunked streaming CSV reader ([8032a81](https://github.com/im-anishraj/arnio/commit/8032a81f3022652df3027bd93fc1ebc0a234c224))
* **csv:** add strict and permissive parser modes ([9cf1e07](https://github.com/im-anishraj/arnio/commit/9cf1e07de25888a90dd3cd68c7f1c1a46e3962f6)), closes [#132](https://github.com/im-anishraj/arnio/issues/132)
* enrich pipeline execution metadata ([348104a](https://github.com/im-anishraj/arnio/commit/348104a4159437f77100106033916afd0f39c2b8)), closes [#166](https://github.com/im-anishraj/arnio/issues/166)
* expose built-in pipeline step signatures ([25cc277](https://github.com/im-anishraj/arnio/commit/25cc277b911b3caad0925df392c581aa03796f8d)), closes [#170](https://github.com/im-anishraj/arnio/issues/170)
* implement configurable missing data values handling ([#783](https://github.com/im-anishraj/arnio/issues/783)) ([765875c](https://github.com/im-anishraj/arnio/commit/765875c75b89da0e641be8b927dfe26935d3482b))
* implement HTML export for DataQualityReport ([#685](https://github.com/im-anishraj/arnio/issues/685)) ([6296568](https://github.com/im-anishraj/arnio/commit/629656896efb18c33f1949f047738b2dbe48972b))
* **io:** add read_jsonl() for JSON Lines support ([095b89d](https://github.com/im-anishraj/arnio/commit/095b89d52d57c6c9be528f7f0d6b4d10462d8383)), closes [#634](https://github.com/im-anishraj/arnio/issues/634)
* **io:** support text file-like inputs in read_csv ([4549170](https://github.com/im-anishraj/arnio/commit/4549170986409d3dc3289506b377f10d884e2d78))
* notebook-friendly DataQualityReport dashboard ([#737](https://github.com/im-anishraj/arnio/issues/737)) ([9e16e18](https://github.com/im-anishraj/arnio/commit/9e16e187be8b20d163660c12c6ddca23133dbbbb))
* **pipeline:** add dry_run validation mode ([2768b4a](https://github.com/im-anishraj/arnio/commit/2768b4aa265fec2c4e5a6df60db418df072cabef))
* **quality:** add compare_profiles helper ([a83c860](https://github.com/im-anishraj/arnio/commit/a83c860ec5ff05c7d3f33a526550e93f456d2a49)), closes [#185](https://github.com/im-anishraj/arnio/issues/185)
* **quality:** add drift gate checks ([#735](https://github.com/im-anishraj/arnio/issues/735)) ([7029151](https://github.com/im-anishraj/arnio/commit/7029151268b8ae1b285e1d2145192c93be8d3879))
* **quality:** add email and URL validity ratios to column profiles ([#176](https://github.com/im-anishraj/arnio/issues/176)) ([#808](https://github.com/im-anishraj/arnio/issues/808)) ([e4a96f9](https://github.com/im-anishraj/arnio/commit/e4a96f9e1a5c64e236ad0d85dd0ba6b5cdf10d49))
* **schema:** add cross-field validation rules parameter ([#651](https://github.com/im-anishraj/arnio/issues/651)) ([36d0545](https://github.com/im-anishraj/arnio/commit/36d054549166542c5401f7a057df25f8a4ab7095)), closes [#196](https://github.com/im-anishraj/arnio/issues/196)
* **schema:** add schema diff helper ([fe82072](https://github.com/im-anishraj/arnio/commit/fe820726cef88ad6ba702decd46bbe29fbcd8999)), closes [#209](https://github.com/im-anishraj/arnio/issues/209)
* **schema:** add warning severity support ([58929c6](https://github.com/im-anishraj/arnio/commit/58929c6047d11800e095cd4e3cbfc95d1f379c4b)), closes [#192](https://github.com/im-anishraj/arnio/issues/192)
* **schema:** bootstrap schema from quality report ([#529](https://github.com/im-anishraj/arnio/issues/529)) ([498d8d4](https://github.com/im-anishraj/arnio/commit/498d8d42deb13119a6f48d59a79562ed68f4ddec))
* support namespaced pipeline steps ([57dec91](https://github.com/im-anishraj/arnio/commit/57dec91f31efbac2f5778af56b9b7afbd3836081)), closes [#168](https://github.com/im-anishraj/arnio/issues/168)
* truncate long ArFrame column names in display ([#566](https://github.com/im-anishraj/arnio/issues/566)) ([66bdc0c](https://github.com/im-anishraj/arnio/commit/66bdc0c9310048ca979389ead3111fcc7e6d8054))
* wrap custom pipeline step errors ([72ddda1](https://github.com/im-anishraj/arnio/commit/72ddda1a9ebf7b32619933e7d177f63e4a861ede))


### Bug Fixes

* align round_numeric_columns subset errors ([#774](https://github.com/im-anishraj/arnio/issues/774)) ([f9a7a4b](https://github.com/im-anishraj/arnio/commit/f9a7a4ba54d635d95d2f5ea2ccfe01bb77412e9e))
* **bindings:** prevent dangling pointer in to_numpy_float/int ([#28](https://github.com/im-anishraj/arnio/issues/28)) ([#805](https://github.com/im-anishraj/arnio/issues/805)) ([f28a207](https://github.com/im-anishraj/arnio/commit/f28a207a9e897a86f242ffd6e42edcd9d73c8669))
* **cleaning:** accept sequence subsets in parse_bool_strings ([#766](https://github.com/im-anishraj/arnio/issues/766)) ([c1c25d6](https://github.com/im-anishraj/arnio/commit/c1c25d619bbccabb9e7df679d607f7075150f686))
* **cleaning:** preserve filter_rows column context on invalid comparisons ([ce10c2f](https://github.com/im-anishraj/arnio/commit/ce10c2f1633c6fecec52a53431783761b4eedc70))
* **cleaning:** preserve Unicode bytes in normalize_case ([ca6afe6](https://github.com/im-anishraj/arnio/commit/ca6afe63397b619ac3f8326ec82bdab31bd9475c)), closes [#26](https://github.com/im-anishraj/arnio/issues/26)
* **cleaning:** reject lossy and non-finite fill_nulls values ([cbd7d81](https://github.com/im-anishraj/arnio/commit/cbd7d81f5bdee6c47385fb46a3ab480a2bcae0ef))
* **cleaning:** validate parse_bool_strings custom tokens ([1036f0b](https://github.com/im-anishraj/arnio/commit/1036f0b0d548af69e947219438208cf54b5a7f8b))
* **csv_writer:** open output file in binary mode ([#752](https://github.com/im-anishraj/arnio/issues/752)) ([088c81f](https://github.com/im-anishraj/arnio/commit/088c81f12c949be14dfb345c3070bc90cc2a51ad)), closes [#717](https://github.com/im-anishraj/arnio/issues/717)
* **csv:** normalize trailing empty fields ([62314d7](https://github.com/im-anishraj/arnio/commit/62314d741c5958b2ffbbd94e9ea362f8909520af)), closes [#116](https://github.com/im-anishraj/arnio/issues/116)
* **csv:** preserve leading-zero identifier inference ([8aa3f15](https://github.com/im-anishraj/arnio/commit/8aa3f15df9724a0c37d6ca2e9578352f012aea21))
* **csv:** reject late NUL bytes in UTF-8 input ([0152a68](https://github.com/im-anishraj/arnio/commit/0152a68510f541efaf845165d4ec53fd34e021e4))
* escape markdown pipes in quality report ([#781](https://github.com/im-anishraj/arnio/issues/781)) ([8ca3074](https://github.com/im-anishraj/arnio/commit/8ca30749a3ab5122a052cd99651b1515d4ffe34d))
* explicitly reject keep=True in drop_duplicates ([#584](https://github.com/im-anishraj/arnio/issues/584)) ([#787](https://github.com/im-anishraj/arnio/issues/787)) ([1d4993a](https://github.com/im-anishraj/arnio/commit/1d4993a99eb55e833a9dd22c59fe5d5b3c8fb188))
* **frame:** enforce consistent column lengths ([#914](https://github.com/im-anishraj/arnio/issues/914)) ([6aab3ea](https://github.com/im-anishraj/arnio/commit/6aab3ea08058bec8af9b7051d636b96831251ecc))
* keep decimal-looking strings on float path ([#788](https://github.com/im-anishraj/arnio/issues/788)) ([d8cea07](https://github.com/im-anishraj/arnio/commit/d8cea0728d938837e1a355cf56f74d82efeffa09))
* make suggested cleaning kwargs deterministic in to_markdown ([#771](https://github.com/im-anishraj/arnio/issues/771)) ([5a280d2](https://github.com/im-anishraj/arnio/commit/5a280d28c5247abb9d5bb34062110c358b422758))
* **pandas:** reject stringified column label collisions ([c3e1d3d](https://github.com/im-anishraj/arnio/commit/c3e1d3d006b0cefd6eefdff38659e94dcc05b7b5)), closes [#711](https://github.com/im-anishraj/arnio/issues/711)
* **pipeline:** raise TypeError for custom steps returning non-DataFra… ([#687](https://github.com/im-anishraj/arnio/issues/687)) ([0008c21](https://github.com/im-anishraj/arnio/commit/0008c21bed342e87d2d27e8f2b960716b62542ee))
* **pipeline:** reject custom steps that shadow built-ins ([b3bf090](https://github.com/im-anishraj/arnio/commit/b3bf0901a6c81999df7bb2e28e88e6ba460410ec))
* preserve non-utf8 scan samples ([da5bf15](https://github.com/im-anishraj/arnio/commit/da5bf15f4ca9add2530e763acb65902c61956f11)), closes [#579](https://github.com/im-anishraj/arnio/issues/579)
* preserve null-valued replace_values results ([#800](https://github.com/im-anishraj/arnio/issues/800)) ([5aaf070](https://github.com/im-anishraj/arnio/commit/5aaf070483e988d3acc7e9effcbb92b6199cf2f8))
* preserve quoted CSV line endings ([8324322](https://github.com/im-anishraj/arnio/commit/8324322d2f32dea78a70dc5fea55e4ccccb4e5f2))
* **quality:** correct compare_profiles drift thresholds ([#750](https://github.com/im-anishraj/arnio/issues/750)) ([f7b72a3](https://github.com/im-anishraj/arnio/commit/f7b72a3e49c65f3cd49c7014db31211382bdb263))
* reject duplicate pandas column labels ([5316cf8](https://github.com/im-anishraj/arnio/commit/5316cf8b3da3c6d552ffc5910748dad29f69cda0))
* reject empty write_csv line terminators ([#757](https://github.com/im-anishraj/arnio/issues/757)) ([859d4b9](https://github.com/im-anishraj/arnio/commit/859d4b998f4428fdf4ef0a3dacec2899c9aa6485))
* reject late nul bytes in csv inputs ([#760](https://github.com/im-anishraj/arnio/issues/760)) ([f140aaf](https://github.com/im-anishraj/arnio/commit/f140aaf31a451c278b408a6f99259288f2e43336))
* reject newline delimiters in write_csv ([#755](https://github.com/im-anishraj/arnio/issues/755)) ([58a265f](https://github.com/im-anishraj/arnio/commit/58a265ff30e86f7f893fa8385adb871bd7a65f3c))
* reject quote delimiter in write_csv ([#756](https://github.com/im-anishraj/arnio/issues/756)) ([3f8c68f](https://github.com/im-anishraj/arnio/commit/3f8c68fdca49c95a60110cf43f2345deb53601ed))
* reject unsupported object scalars ([75af857](https://github.com/im-anishraj/arnio/commit/75af85757e9680ae48ea231863199b723e8f3ad9))
* resolve CountryCode validator allowlist and uniqueness ([eb7b34f](https://github.com/im-anishraj/arnio/commit/eb7b34fcb75b78d5e6803e1c0d19d734f47a3ca3)), closes [#714](https://github.com/im-anishraj/arnio/issues/714)
* respect non-utf8 scan sample count ([#761](https://github.com/im-anishraj/arnio/issues/761)) ([4cd43c5](https://github.com/im-anishraj/arnio/commit/4cd43c5befc5bddd28ce896e6a6254f634af8f12))
* **schema:** add redaction support to markdown validation reports ([e523129](https://github.com/im-anishraj/arnio/commit/e5231293b2825c47ed7f09d88b3d9287458a7513)), closes [#682](https://github.com/im-anishraj/arnio/issues/682)
* **schema:** reject invalid unique configuration in validate ([a960498](https://github.com/im-anishraj/arnio/commit/a9604986aaf5330a84ba2344ddd54bf5afbbb4cf))
* support headerless schema scanning ([acc7b1e](https://github.com/im-anishraj/arnio/commit/acc7b1e5a0a67d7ead77e119e880c1faf1c986d2))
* use one-based composite unique row indexes ([#782](https://github.com/im-anishraj/arnio/issues/782)) ([cdd1368](https://github.com/im-anishraj/arnio/commit/cdd1368ea9520360965cdcb99337df913f421b51))
* validate drop_duplicates keep option ([#758](https://github.com/im-anishraj/arnio/issues/758)) ([a12a5b1](https://github.com/im-anishraj/arnio/commit/a12a5b1dba68d5c30064c0f41dff954df923b5c6))
* validate pipeline steps before execution ([#693](https://github.com/im-anishraj/arnio/issues/693)) ([d102429](https://github.com/im-anishraj/arnio/commit/d102429eced6a92c83cb3d6d1728bf810ea9ba7d))
* validate schema field values early ([#748](https://github.com/im-anishraj/arnio/issues/748)) ([bf9d6ba](https://github.com/im-anishraj/arnio/commit/bf9d6bab605235841f60f61179838adca0e8d949))
* validate Schema.unique string and invalid unique members ([#776](https://github.com/im-anishraj/arnio/issues/776)) ([866ffc5](https://github.com/im-anishraj/arnio/commit/866ffc59240542300dae27a97fcda878c9abaea6))
* validate UInt64 conversion bounds ([32ae8a4](https://github.com/im-anishraj/arnio/commit/32ae8a43d2858c14d32122d236767d5d1453a837)), closes [#626](https://github.com/im-anishraj/arnio/issues/626)
* validate write_csv delimiter type ([#759](https://github.com/im-anishraj/arnio/issues/759)) ([ca69adf](https://github.com/im-anishraj/arnio/commit/ca69adf1980c07d7866e64ad11f1255b0d98b384))


### Performance Improvements

* add approximate top-values profiling ([#762](https://github.com/im-anishraj/arnio/issues/762)) ([0d1168b](https://github.com/im-anishraj/arnio/commit/0d1168b0d294310f0772496b6f1290d6e9e8ac0c))
* add measurement script for to_pandas conversion overhead ([#556](https://github.com/im-anishraj/arnio/issues/556)) ([6c15c53](https://github.com/im-anishraj/arnio/commit/6c15c5337ea09cdbe552733e871e09adca704895))
* add multiline CSV benchmark coverage ([5f850f2](https://github.com/im-anishraj/arnio/commit/5f850f2e7c2c2bab3214f66e9844f326eb8921be))
* **cleaning:** add native safe_divide_columns numeric path ([7179a95](https://github.com/im-anishraj/arnio/commit/7179a953472f39892ac4063d1cedd6e6c35d739f))
* **cleaning:** implement native clip_numeric without pandas round-trip ([eed031f](https://github.com/im-anishraj/arnio/commit/eed031f02c01f48db21f6a7c005dc310cc7d205c)), closes [#657](https://github.com/im-anishraj/arnio/issues/657)
* native normalize_unicode without pandas roundtrip ([38a6860](https://github.com/im-anishraj/arnio/commit/38a6860638f79035973899d6023829fef5c76624))


### Documentation

* add CLI roadmap and command examples ([1f4f61d](https://github.com/im-anishraj/arnio/commit/1f4f61d5a1c013179ec914931a713a5a833310e5)), closes [#671](https://github.com/im-anishraj/arnio/issues/671)
* add CSV error handling guidance ([10aa0b7](https://github.com/im-anishraj/arnio/commit/10aa0b70f18026671ac9baeb94443fa27b2d46aa)), closes [#490](https://github.com/im-anishraj/arnio/issues/490)
* add data contract CI workflow example ([ab83194](https://github.com/im-anishraj/arnio/commit/ab83194e81e667997cce23d30663d1efac33616f))
* add examples for common messy datasets ([ab27ea7](https://github.com/im-anishraj/arnio/commit/ab27ea7765af6372d2bb7b3fbf4dba4186921433))
* add JSONL pipeline processing example ([8db4886](https://github.com/im-anishraj/arnio/commit/8db48867e90591fbd2ff0f7be1764c6165ab77a5)), closes [#864](https://github.com/im-anishraj/arnio/issues/864)
* add pipeline backend execution map ([#744](https://github.com/im-anishraj/arnio/issues/744)) ([e4f368e](https://github.com/im-anishraj/arnio/commit/e4f368ecd343e5d513a5c1d71a55b7e98d3925ce))
* add profiling privacy and redaction guide ([#862](https://github.com/im-anishraj/arnio/issues/862)) ([cc07ed3](https://github.com/im-anishraj/arnio/commit/cc07ed3fa9e8ecbe6483ab4d0b604028f5d8e636))
* add quick example section to README ([#794](https://github.com/im-anishraj/arnio/issues/794)) ([c9a59a2](https://github.com/im-anishraj/arnio/commit/c9a59a2b2cf4b94033538f1242598db4942fe84b))
* add troubleshooting guide ([#791](https://github.com/im-anishraj/arnio/issues/791)) ([7f3d607](https://github.com/im-anishraj/arnio/commit/7f3d60701db10db1471670308c3642004bfd72ca))
* document auto_clean strict mode risks ([#764](https://github.com/im-anishraj/arnio/issues/764)) ([12c6b36](https://github.com/im-anishraj/arnio/commit/12c6b36f340563cd4ab482b459fb3b0aa437e5e8))
* document sklearn row-dropping pipeline behavior ([#786](https://github.com/im-anishraj/arnio/issues/786)) ([371f886](https://github.com/im-anishraj/arnio/commit/371f886a1a74c3e86f28683331cae9daf3655413))
* document ValidationResult row-index convention (1-based, header excluded) ([#803](https://github.com/im-anishraj/arnio/issues/803)) ([a4f3965](https://github.com/im-anishraj/arnio/commit/a4f3965cc9d74cc2f62d6ab4bba81136ffb62c3b))
* document write_csv validation behavior ([4588666](https://github.com/im-anishraj/arnio/commit/45886660c5087d80ab2aeb39ebd64562836805e8)), closes [#664](https://github.com/im-anishraj/arnio/issues/664)
* standardize Google-style docstrings in arnio/schema.py ([dc5aa3d](https://github.com/im-anishraj/arnio/commit/dc5aa3d9036651c1190884ca376f1f0090796f98))

## [1.14.0](https://github.com/im-anishraj/arnio/compare/v1.13.0...v1.14.0) (2026-05-18)


### Features

* add parse_bool_strings pipeline step ([bc6e53d](https://github.com/im-anishraj/arnio/commit/bc6e53d6cbf73c02bcbd81f828a6c085ed928797)), closes [#150](https://github.com/im-anishraj/arnio/issues/150)


### Documentation

* add interoperability examples ([aa7c7d7](https://github.com/im-anishraj/arnio/commit/aa7c7d77d1dcca8a6b7f416ef358a4c6f7ac8edc))

## [1.13.0](https://github.com/im-anishraj/arnio/compare/v1.12.1...v1.13.0) (2026-05-18)


### Features

* add benchmark regression reporting ([#554](https://github.com/im-anishraj/arnio/issues/554)) ([83b9ee5](https://github.com/im-anishraj/arnio/commit/83b9ee5c8cf75477ebb476f1fb3f13654eceab3a))
* add quality sample redaction ([#555](https://github.com/im-anishraj/arnio/issues/555)) ([daece46](https://github.com/im-anishraj/arnio/commit/daece46037eab5bc924d8e61b4111dc659301ed9))
* add Regex field validator to schema ([#537](https://github.com/im-anishraj/arnio/issues/537)) ([70b1839](https://github.com/im-anishraj/arnio/commit/70b18395066c424e143a1a8eb034f3f200d92333))
* add string length statistics to quality profile (resolves [#174](https://github.com/im-anishraj/arnio/issues/174)) ([#550](https://github.com/im-anishraj/arnio/issues/550)) ([98d1bf3](https://github.com/im-anishraj/arnio/commit/98d1bf34a9b175610efbb360d034ce0663a8a547))

## [1.12.1](https://github.com/im-anishraj/arnio/compare/v1.12.0...v1.12.1) (2026-05-18)


### Bug Fixes

* make custom pipeline step registry thread-safe ([2755772](https://github.com/im-anishraj/arnio/commit/27557721616a078d4302f9cc7aa2e9f2750b96f5))


### Performance Improvements

* release GIL around long C++ operations ([1100fec](https://github.com/im-anishraj/arnio/commit/1100fec21ad05a6288a945af1e88754b7a787280))

## [1.12.0](https://github.com/im-anishraj/arnio/compare/v1.11.3...v1.12.0) (2026-05-17)


### Features

* add strip_whitespace allocation benchmark ([e2ff584](https://github.com/im-anishraj/arnio/commit/e2ff58416125fe1eae4bef4c204cc52fb248fb86))


### Documentation

* replace ASCII architecture diagram with Mermaid flowchart ([abede39](https://github.com/im-anishraj/arnio/commit/abede392dfd11ac909d273c90cfc01463522004b))

## [1.11.3](https://github.com/im-anishraj/arnio/compare/v1.11.2...v1.11.3) (2026-05-17)


### Documentation

* add API reference skeleton ([5ea384d](https://github.com/im-anishraj/arnio/commit/5ea384d9341aab15fdbe053ff0388d8f1430cf48))

## [1.11.2](https://github.com/im-anishraj/arnio/compare/v1.11.1...v1.11.2) (2026-05-17)


### Bug Fixes

* raise clear errors for unsupported pandas dtypes in from_pandas ([1791e4f](https://github.com/im-anishraj/arnio/commit/1791e4f05242841e7878fd8c03a185bb01c48ae1))
* preserve 1-based source row numbers in schema validation issues ([5f538fd](https://github.com/im-anishraj/arnio/commit/5f538fd2b508b4c791967c8f9b1947387c6467c2))

## [1.11.1](https://github.com/im-anishraj/arnio/compare/v1.11.0...v1.11.1) (2026-05-17)


### Bug Fixes

* skip numeric cast suggestions for identifier-like columns ([cf687e2](https://github.com/im-anishraj/arnio/commit/cf687e2ae83b4cc1c1edef6065920a12fbc7a7ad))

## [1.11.0](https://github.com/im-anishraj/arnio/compare/v1.10.0...v1.11.0) (2026-05-17)


### Features

* add scikit-learn ArnioCleaner transformer ([610a39f](https://github.com/im-anishraj/arnio/commit/610a39fe5ab4a02db2ad7f9c3223896cdf263db5))
* register combine_columns as pipeline step and add test ([beaf402](https://github.com/im-anishraj/arnio/commit/beaf4022ac7dc70cb370d387769fc033beb4454d))

## [1.10.0](https://github.com/im-anishraj/arnio/compare/v1.9.1...v1.10.0) (2026-05-17)


### Features

* add DateTime schema field ([05c26be](https://github.com/im-anishraj/arnio/commit/05c26bebf1cf79bbdbb98157dba1618c61abd08e))
* add normalize_unicode cleaning step ([c8c7c40](https://github.com/im-anishraj/arnio/commit/c8c7c40c9172e83d289b25e2e4b797efd78cd26a))
* add top_values summary for categorical columns ([f593f94](https://github.com/im-anishraj/arnio/commit/f593f94cf331180f29516d1afc217c106a96ad8b))


### Performance Improvements

* add process RSS metrics to benchmark ([6206cbd](https://github.com/im-anishraj/arnio/commit/6206cbda592705d20877d8a89e2f899025f2f329))


### Documentation

* add financial CSV cleaning example notebook ([e9fb6f6](https://github.com/im-anishraj/arnio/commit/e9fb6f6f793538354160584effd87bf866f85eee))

## [1.9.1](https://github.com/im-anishraj/arnio/compare/v1.9.0...v1.9.1) (2026-05-17)


### Performance Improvements

* stream transcode and sample rows for scan_csv schema inference ([713aeaa](https://github.com/im-anishraj/arnio/commit/713aeaa9ccb380bb68568999edc141e1dc73389b))

## [1.9.0](https://github.com/im-anishraj/arnio/compare/v1.8.0...v1.9.0) (2026-05-17)


### Features

* add composite uniqueness validation support ([#495](https://github.com/im-anishraj/arnio/issues/495)) ([8b11e19](https://github.com/im-anishraj/arnio/commit/8b11e19180b97fde1c380857e702d78dc7df8fc8))
* add CountryCode schema validator ([#487](https://github.com/im-anishraj/arnio/issues/487)) ([14a77e5](https://github.com/im-anishraj/arnio/commit/14a77e532409bffc0fdef85fbbbaaa798782dde7))
* add replace_values pipeline step ([#348](https://github.com/im-anishraj/arnio/issues/348)) ([02b297c](https://github.com/im-anishraj/arnio/commit/02b297c0d60fdb4417e801f2f28db92f50441a4c))


### Documentation

* document pandas index conversion behavior ([#407](https://github.com/im-anishraj/arnio/issues/407)) ([327b650](https://github.com/im-anishraj/arnio/commit/327b650bb40b8ba902c5b0dc903b98d5f3e1172e))

## [1.8.0](https://github.com/im-anishraj/arnio/compare/v1.7.0...v1.8.0) (2026-05-17)


### Features

* add ArFrame.select_dtypes for type-based column selection ([7899541](https://github.com/im-anishraj/arnio/commit/7899541113aad0f300decc08b94f285b920f3008))
* add trim_column_names cleaning primitive and pipeline step ([d064335](https://github.com/im-anishraj/arnio/commit/d0643355f1f626a4ee2a4264aea67e316971df76))


### Bug Fixes

* reject impossible schema bounds ([906b286](https://github.com/im-anishraj/arnio/commit/906b286ad0bae551bea56746f90fa95135f749ab))

## [1.7.0](https://github.com/im-anishraj/arnio/compare/v1.6.2...v1.7.0) (2026-05-17)


### Features

* add keep_rows_with_nulls pipeline step ([37dde00](https://github.com/im-anishraj/arnio/commit/37dde009d3899e3647183f34209f171afca11f31))


### Bug Fixes

* add YAML validation for GitHub workflow files ([0c666ca](https://github.com/im-anishraj/arnio/commit/0c666caa0ce937d70fdffc58dee2e8ba12338412))


### Performance Improvements

* add auto-clean memory benchmark ([8bd10f4](https://github.com/im-anishraj/arnio/commit/8bd10f4c7301d210a0dcebb64d27006274308705))

## [1.6.2](https://github.com/im-anishraj/arnio/compare/v1.6.1...v1.6.2) (2026-05-17)


### Documentation

* improve quickstart wording ([a3f37d9](https://github.com/im-anishraj/arnio/commit/a3f37d94146f5f1b3939b0962236242312dadcac))

## [1.6.1](https://github.com/im-anishraj/arnio/compare/v1.6.0...v1.6.1) (2026-05-16)


### Bug Fixes

* preserve column order in scan_csv schema ([a3864f0](https://github.com/im-anishraj/arnio/commit/a3864f0640580acdf979d71c18c25ce8c6a9456d))
* validate missing columns in filter_rows ([e0514ef](https://github.com/im-anishraj/arnio/commit/e0514ef04fea19fb07fd7373539e1a5019e2763b))

## [1.6.0](https://github.com/im-anishraj/arnio/compare/v1.5.1...v1.6.0) (2026-05-16)


### Features

* add to_pandas copy option ([1746fe1](https://github.com/im-anishraj/arnio/commit/1746fe15d5c399d649fff9561a7a02bea147c4de))

## [1.5.1](https://github.com/im-anishraj/arnio/compare/v1.5.0...v1.5.1) (2026-05-16)


### Bug Fixes

* normalize title case across punctuation boundaries ([4a9b947](https://github.com/im-anishraj/arnio/commit/4a9b947f4045edf61839e70247fcce5b54fe5b1d))

## [1.5.0](https://github.com/im-anishraj/arnio/compare/v1.4.0...v1.5.0) (2026-05-16)


### Features

* add is_empty convenience property to ArFrame ([37df94d](https://github.com/im-anishraj/arnio/commit/37df94d0e4f782fc4510ea8ad179960f51c0fc7d))
* add validation summary counts ([#444](https://github.com/im-anishraj/arnio/issues/444)) ([6575491](https://github.com/im-anishraj/arnio/commit/657549174aaca524ce77f169a7e7b3a7b230cba0))


### Bug Fixes

* allow encoded csv nul handling ([5796a35](https://github.com/im-anishraj/arnio/commit/5796a35a32aff5a5d889a72deee255232c527929)), closes [#422](https://github.com/im-anishraj/arnio/issues/422)

## [1.4.0](https://github.com/im-anishraj/arnio/compare/v1.3.1...v1.4.0) (2026-05-16)


### Features

* add bounded profiling sample_size validation ([1e31269](https://github.com/im-anishraj/arnio/commit/1e3126986bdc21e128fc734a71a77aa7f242441a))

## [1.3.1](https://github.com/im-anishraj/arnio/compare/v1.3.0...v1.3.1) (2026-05-16)


### Bug Fixes

* handle empty CSV files with a dedicated error path ([b359173](https://github.com/im-anishraj/arnio/commit/b359173f15b5cf6b4cb68b9f04b418d5380c0c44))

## [1.3.0](https://github.com/im-anishraj/arnio/compare/v1.2.0...v1.3.0) (2026-05-15)


### Features

* add column existence validation helper ([517d1e0](https://github.com/im-anishraj/arnio/commit/517d1e07d3b19252027ecdfac23d17b19e0aa793))
* add pandas integration direction ([#399](https://github.com/im-anishraj/arnio/issues/399)) ([22f9b58](https://github.com/im-anishraj/arnio/commit/22f9b58458383549d97d81ff7828b7a047063525))
* **convert:** preserve DataFrame attrs roundtrip ([4018f27](https://github.com/im-anishraj/arnio/commit/4018f27f76dbb021591b4aa6844e2c130887dceb))


### Bug Fixes

* preserve Int64 dtype for all-null nullable integer columns in from_pandas roundtrip ([#394](https://github.com/im-anishraj/arnio/issues/394)) ([ef726ed](https://github.com/im-anishraj/arnio/commit/ef726ed0e1af588c7c0f74a04e02ccfd6a1d688f))


### Documentation

* add quality and schema architecture flow ([d22fa56](https://github.com/im-anishraj/arnio/commit/d22fa56c393c2005c9a351f30ca6132c4ae3c863))

## [1.2.0](https://github.com/im-anishraj/arnio/compare/v1.1.1...v1.2.0) (2026-05-15)


### Features

* add ArFrame preview method ([814102e](https://github.com/im-anishraj/arnio/commit/814102e35b153cf75b3a759a5e33867edfe03321))
* add ArFrame select_columns helper ([fff406d](https://github.com/im-anishraj/arnio/commit/fff406d9a10943cb6f2bd76d32240933da90ed51))
* add clip_numeric cleaning helper ([4022449](https://github.com/im-anishraj/arnio/commit/4022449c7bbe5e31c94e756ff29a36b4c274a232))
* add drop constant columns ([#357](https://github.com/im-anishraj/arnio/issues/357)) ([3e13d3d](https://github.com/im-anishraj/arnio/commit/3e13d3d576add9fd8113cdf185ca08e61e75c4ee))
* add filter_rows pipeline step ([#288](https://github.com/im-anishraj/arnio/issues/288)) ([a3b7386](https://github.com/im-anishraj/arnio/commit/a3b7386e75bc45c9a7fde403ea373334ef528f75))
* add refactor task issue template ([#334](https://github.com/im-anishraj/arnio/issues/334)) ([6690947](https://github.com/im-anishraj/arnio/commit/6690947bcada6dc825853036a11ad2310acdd4e4))
* add round_numeric_columns cleaning helper ([61cd110](https://github.com/im-anishraj/arnio/commit/61cd1105e60c6daa38d34ef602f3f9fac28de7ea))
* add safe_divide_columns cleaning step ([80e4a65](https://github.com/im-anishraj/arnio/commit/80e4a654d81a1bd95e96b1f5ec83f5f82deff590))
* add trim_headers CSV option ([022460e](https://github.com/im-anishraj/arnio/commit/022460e1fa7e9510960a789aa38f835731dec700))
* add ValidationResult.to_markdown ([168e525](https://github.com/im-anishraj/arnio/commit/168e525409ce3a8d60f972dadacfaab01c4cafa8))
* enhance pull request template with media and performance sections ([#336](https://github.com/im-anishraj/arnio/issues/336)) ([99b588b](https://github.com/im-anishraj/arnio/commit/99b588b62910a68b83abdb39455c0d59de6bba56))


### Bug Fixes

* improve nested object error messages in from_pandas ([ca90974](https://github.com/im-anishraj/arnio/commit/ca90974cdef4b25824525aa2d4482968054adba2))


### Documentation

* add beginner-friendly auto_clean tutorial with profiling and cleaning workflow  ([#326](https://github.com/im-anishraj/arnio/issues/326)) ([b604a0d](https://github.com/im-anishraj/arnio/commit/b604a0d067f6603cf6bb5037b5b33b6ff0c19248))
* add contributor glossary ([#308](https://github.com/im-anishraj/arnio/issues/308)) ([da52804](https://github.com/im-anishraj/arnio/commit/da5280486603e2d630adf33ec8d7162acb9ba0ba))
* add data quality report examples [#279](https://github.com/im-anishraj/arnio/issues/279) ([#295](https://github.com/im-anishraj/arnio/issues/295)) ([ca42e87](https://github.com/im-anishraj/arnio/commit/ca42e87cf2c596b78286ab3fe4ce8a9c305a6f2a))
* add Discord community links ([#305](https://github.com/im-anishraj/arnio/issues/305)) ([64cb4a1](https://github.com/im-anishraj/arnio/commit/64cb4a1d871ac7ec8471e28c5386eb8ebfb20ef4))
* add gssoc faq ([#309](https://github.com/im-anishraj/arnio/issues/309)) ([dc32e56](https://github.com/im-anishraj/arnio/commit/dc32e563ba5ff8e2ed2680dec9451d27c65a14e5))
* add issue triage guide for maintainers ([#300](https://github.com/im-anishraj/arnio/issues/300)) ([2d6dd6f](https://github.com/im-anishraj/arnio/commit/2d6dd6f9c566479757c2146f02e186c1d7d57c2e))
* add release process guide ([#304](https://github.com/im-anishraj/arnio/issues/304)) ([f5e1325](https://github.com/im-anishraj/arnio/commit/f5e13252889865e24cd464379c9fa3974d2fff03))
* align pandas dtype support documentation with implementation ([#327](https://github.com/im-anishraj/arnio/issues/327)) ([badd815](https://github.com/im-anishraj/arnio/commit/badd8150a3859ffb1598bdf21f71a8cd2c4c6b0b))
* fix non-sequential roadmap versions ([#107](https://github.com/im-anishraj/arnio/issues/107)) ([db3b8e4](https://github.com/im-anishraj/arnio/commit/db3b8e47fc721ad899df0b6239bc706824d168a5))
* remove large Discord badge from README ([#307](https://github.com/im-anishraj/arnio/issues/307)) ([1f0ff3a](https://github.com/im-anishraj/arnio/commit/1f0ff3ab15d111344cc9c6281226ef6361f919f9))

## [1.1.1](https://github.com/im-anishraj/arnio/compare/v1.1.0...v1.1.1) (2026-05-14)


### Documentation

* prepare repository for GSSoC contributors ([#289](https://github.com/im-anishraj/arnio/issues/289)) ([d270812](https://github.com/im-anishraj/arnio/commit/d2708126a20d6e12be75a438d631f84aa802e13f))

## [1.1.0](https://github.com/im-anishraj/arnio/compare/v1.0.2...v1.1.0) (2026-05-14)


### Features

* add data quality engine ([6053ab9](https://github.com/im-anishraj/arnio/commit/6053ab93fa29b706a20f5fd8d905f046fedb36c5))
* add data quality engine ([f8abb2f](https://github.com/im-anishraj/arnio/commit/f8abb2f8202e9d1fa394a2e1e97576f003d113b0))

## [1.0.2](https://github.com/im-anishraj/arnio/compare/v1.0.1...v1.0.2) (2026-05-10)


### Documentation

* add language identifiers to unlabeled fenced code blocks (MD040) ([21aad9c](https://github.com/im-anishraj/arnio/commit/21aad9c06e1440efa20d377f7842da6afa8d9095))
* completely redesign README with flagship-quality presentation ([252988a](https://github.com/im-anishraj/arnio/commit/252988a770a0600074734ed44b48e7cbd6763a66))
* completely redesign README with flagship-quality presentation ([5953eb4](https://github.com/im-anishraj/arnio/commit/5953eb4a567e9941a9a5ff3c4bc892a19605c737))

## [1.0.1](https://github.com/im-anishraj/arnio/compare/v1.0.0...v1.0.1) (2026-05-09)


### Documentation

* add architecture guide, reframe benchmarks, add social preview ([f91e69e](https://github.com/im-anishraj/arnio/commit/f91e69e7ffb89adcaa4ed64a5ddd4173e889c045))
* add architecture guide, reframe benchmarks, add social preview ([ab2ddba](https://github.com/im-anishraj/arnio/commit/ab2ddbaf422b582b5fc855df71906612936568e9))
* add comprehensive docstrings to all public Python functions ([3cbe1b3](https://github.com/im-anishraj/arnio/commit/3cbe1b35b95678ecc7aa267663dcd998dd74d0f2))
* duplicated code ([62401a1](https://github.com/im-anishraj/arnio/commit/62401a1418acb149b74697495467fd05e22fa14f))
* enforce conventional commits in contributor guidelines ([d98f6cf](https://github.com/im-anishraj/arnio/commit/d98f6cf208f8acc5d34dc0bee280f28a64cc1dbe))
* remove duplicated code ([0e215f9](https://github.com/im-anishraj/arnio/commit/0e215f9080abbe77183f51a9a1b07e90d60bc54f))

## [Unreleased]
### Fixed
- Fixed type consistency check in Column (#52)

## [1.0.0] - 2026-05-08
### Added
- **Cross-Platform Wheels**: Full `cibuildwheel` automation delivering pre-compiled native wheels for Windows, Linux, and macOS (Intel & Apple Silicon).
- **Google Colab Compatibility**: Linux wheels are now fully `manylinux` compliant, allowing `pip install arnio` to work out-of-the-box on Colab and Ubuntu.
- **Production-Grade Packaging**: Resolved `ModuleNotFoundError` by removing double-nesting issues in `scikit-build-core` config.
- **CI/CD Excellence**: Fully automated PyPI publishing pipeline via Trusted Publishing with integrated source distributions (`sdist`).
- **Stable API**: Officially marked `arnio` as stable for production workloads with "Development Status :: 5 - Production/Stable".

### Fixed
- Migrated from `FetchContent` to `find_package(pybind11)` for faster, offline, and more robust cross-platform builds.
- Refactored `cibuildwheel` configuration entirely into `pyproject.toml` for standard and declarative packaging.

## [0.1.3] - 2026-05-06
### Fixed
- `normalize_case()` now accepts `case_type` kwarg as documented in README
  (previously accepted `case=`, causing TypeError for all README users)
- `to_pandas()` completely rewritten using zero-copy NumPy buffer interface —
  eliminates O(rows × cols) pybind11 boundary crossings, restoring actual 
  performance advantage over pandas
- `from_pandas()` implemented with correct null handling and round-trip fidelity

### Added
- `ar.register_step(name, fn)` — register pure-Python pipeline steps without C++
- `arnio.exceptions` module with `ArnioError`, `UnknownStepError`, `CsvReadError`, 
  `TypeCastError` — replaces opaque C++ errors with actionable messages
- `arnio.__version__` now available programmatically
- `benchmarks/generate_data.py` — deterministic 1M row test dataset generator
- `benchmarks/benchmark_vs_pandas.py` — reproducible end-to-end benchmark

### Fixed (Internal)
- CI now verifies compilation on Ubuntu and Windows across Python 3.9–3.12

## [0.1.2] - 2026-05-03
### Fixed
- Stability improvements and initial PyPI release

# TODO: issue #2423
