# Changelog

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
