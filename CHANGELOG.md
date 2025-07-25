# CHANGELOG

## v1.0.5 (2025-07-25)

### Bug fixes 

* cli_tools: Adjustment to fix original issue ([`9018af6`](https://github.com/BAMresearch/McSAS3/commit/9018af6b730b0464c22e11e9ef7a17da63cbddb2))

### Unknown Scope

* Fix(cli_tools): Cannot require extra unused parameters in histogrammer and optimizer ([`90dce04`](https://github.com/BAMresearch/McSAS3/commit/90dce04f107b64b644ead1230231bb01eaf068dc))

## v1.0.4 (2025-07-24)

### Bug fixes 

* GHA: don't run optimizer tests, takes too long ([`2632265`](https://github.com/BAMresearch/McSAS3/commit/2632265b24b799cca93b096fca74b026b6ce73d7))

* mc_plot: figure out available monospace font once before using it for the result card ([`5bc2721`](https://github.com/BAMresearch/McSAS3/commit/5bc27217628822cac2b300c9ec13d8e8f72dfffc))

* __main__: show Error type name instead of the generic ERROR ([`bc8643e`](https://github.com/BAMresearch/McSAS3/commit/bc8643e0a4799156b799e2c9e60f1d99b7f8aa18))

* __main__: show usage with no cmdline args or on error, move example file paths to argument help ([`f05d00a`](https://github.com/BAMresearch/McSAS3/commit/f05d00ac60d555ed6909b97bdb8fbe05cef5594e))

* cli_tools: dummy attributes added to be compatible with the same kwargs supplied at the end of __main__ ([`a5e8989`](https://github.com/BAMresearch/McSAS3/commit/a5e89892978e458c11bfd9cff91b75bd8cb76b02))

* Project: dependencies to install when installing this package ([`6e3ecd6`](https://github.com/BAMresearch/McSAS3/commit/6e3ecd6bfc40c0f22c39f9be07b7693131a589c8))

### Code style 

* mc_plot: reformatting ([`6b637d7`](https://github.com/BAMresearch/McSAS3/commit/6b637d733f43501d56071a46abd98019f478d8df))

* mc_plot: remove disables imports ([`851ae43`](https://github.com/BAMresearch/McSAS3/commit/851ae435d9dc4224971d33cb492fe17c8d3dc50d))

* imports: isort'd ([`de09bd4`](https://github.com/BAMresearch/McSAS3/commit/de09bd4d8580cc7fb77bd84404f7eee8254395f4))

* formatting: accepted by flake8 now, isort+black applied ([`ead1388`](https://github.com/BAMresearch/McSAS3/commit/ead1388d03676fb28fc1e98596d30282145b7a43))

### Continuous integration 

* templates: remove old templates and postprocessing from obsolete cookiecutter cfg ([`d52e29b`](https://github.com/BAMresearch/McSAS3/commit/d52e29b998f1d2fe83862aae8a71787bcdbb28d3))

### Documentation 

* readme: merging artifact removed ([`997da1b`](https://github.com/BAMresearch/McSAS3/commit/997da1b64ae22b4abfa70a1f304d15418d23f71a))

* changelog: unknown section renamed, due to template update ([`fe818f0`](https://github.com/BAMresearch/McSAS3/commit/fe818f0cea7d4b94f59b0304d74cba6d84fee8d3))

* readme: notes on updating from project template ([`aa08975`](https://github.com/BAMresearch/McSAS3/commit/aa08975cfe6a25c4d8aba6f25c3d530b89a721f8))

* changelog: unknown section renamed, due to template update ([`59af50a`](https://github.com/BAMresearch/McSAS3/commit/59af50a43a00ce664631fe503cbfb38fa5d94e97))

* readme: move description after batches, due to template update ([`75918f9`](https://github.com/BAMresearch/McSAS3/commit/75918f99103acb6b05c681e97dfe554cafc40506))

* authors: updated ([`af34b16`](https://github.com/BAMresearch/McSAS3/commit/af34b16cd1100ef9aa4061d401858d4e4bb6ddc3))

### Refactoring 

* mc_plot: imports isort'd ([`f1ad72a`](https://github.com/BAMresearch/McSAS3/commit/f1ad72a4a83446e5da18bca186d1bea80c38ac10))

* McModel: common dict for composed parameters ([`255c52c`](https://github.com/BAMresearch/McSAS3/commit/255c52cf0bb157c71d81bb15dfd02fc7433b294f))

### Testing 

* Notebook: update to current messages returned from McSAS3 ([`92de43c`](https://github.com/BAMresearch/McSAS3/commit/92de43c37da64443e6ace5f7fb87159e6bd37d3e))

* optimizer_integraltest: correct model parameter is *scale* now, instead of *scaling* ([`b060136`](https://github.com/BAMresearch/McSAS3/commit/b060136ece2e7dd86eaf599285c4b943e917517e))

* Notebook: update and fixes ([`7488477`](https://github.com/BAMresearch/McSAS3/commit/7488477724d3f0173c4971dcba83bd69786d7404))

* setup: attempt to fix PytestRemovedIn9Warning ([`ad010bc`](https://github.com/BAMresearch/McSAS3/commit/ad010bce056fb5cde418e72a6f91731d1408536e))

### Unknown Scope

* doc(__main__): note on incompatible default path for installed package ([`37f7e1d`](https://github.com/BAMresearch/McSAS3/commit/37f7e1d31d7a3b07b3981c1937c8bd0ff9831d22))

* overlooked unit ([`0f1fa7d`](https://github.com/BAMresearch/McSAS3/commit/0f1fa7d14aa3b855407e1391bfb7dff5f9223139))

* adjustments break quickstartdemo speed.. reverting ([`88ff90f`](https://github.com/BAMresearch/McSAS3/commit/88ff90fe72f9f5595ec8daf422d76d4e1d5d5085))

* optimizing the auto-limit modification ([`988583e`](https://github.com/BAMresearch/McSAS3/commit/988583ede6dca872dbb6f7b5838fe00a6c3f6aa1))

* A little improvement in the automatic sizing, particularly useful for powders and samples with strong large-structure scattering contributions ([`986ee40`](https://github.com/BAMresearch/McSAS3/commit/986ee40f39b11eab67ff2c73f0470e08ba55f44a))

* Small fix ([`b8a7e9e`](https://github.com/BAMresearch/McSAS3/commit/b8a7e9e0cb61bc01dd5929f77e01a4ed4ce4306a))

* fix ([`40f74ae`](https://github.com/BAMresearch/McSAS3/commit/40f74ae3b30e3d794eed998bd82740db2ef9ce20))

* Beta-testing a logRandom flag for log-transforming the random number generator ([`376a216`](https://github.com/BAMresearch/McSAS3/commit/376a216d2dfc5c79da1ce0e09aff53a8da25f34f))

* Reduce debug output ([`f8e6c91`](https://github.com/BAMresearch/McSAS3/commit/f8e6c9190c20ef35d4120a8d39277926bc48441e))

* Update README.rst ([`7ea1115`](https://github.com/BAMresearch/McSAS3/commit/7ea11156216b23955ab1bf6217e1351a08e5c0f3))

* cli tools now installed with pip install ([`dfcb380`](https://github.com/BAMresearch/McSAS3/commit/dfcb380841223264ca566572387256572828229d))

* small fix ([`6e0c4ca`](https://github.com/BAMresearch/McSAS3/commit/6e0c4cad08d5d93473e176914d7f7dae93a09f75))

* Reorganize to enable command-line tools via pip install ([`473b250`](https://github.com/BAMresearch/McSAS3/commit/473b250503dc181b45e38765de97dad9213f7ae6))

* Add warnings in case MixtureModels are attempted ([`4a9d86e`](https://github.com/BAMresearch/McSAS3/commit/4a9d86ec4ed346b726232b2ce73a06a84ad7c68c))

* test IEmin ([`10de982`](https://github.com/BAMresearch/McSAS3/commit/10de982d2a922c73d2463841589801fe3972cdfd))

* Small change to prevent issues when loading Nones ([`b72d791`](https://github.com/BAMresearch/McSAS3/commit/b72d79159347e9170ccffc215edab078b764bafb))

* all tests passing ([`a39395b`](https://github.com/BAMresearch/McSAS3/commit/a39395b68634fa8eb537973e1c1c3c9c3f8df46f))

* small fixes in unit tests ([`fdef730`](https://github.com/BAMresearch/McSAS3/commit/fdef7304e9d54fea8c660e8fb82c8a8c4e5ca6af))

* Fix to McData for actually loading rawData from a prior run. ([`8b58966`](https://github.com/BAMresearch/McSAS3/commit/8b589660427ec19508bf2b427169148d56205a77))

* adjustments to mc_hdf ([`af28623`](https://github.com/BAMresearch/McSAS3/commit/af2862338881bba3367eb78f98a12c0485d6b65d))

* Consistent file naming and an improved McHDF class ([`a8e2117`](https://github.com/BAMresearch/McSAS3/commit/a8e21179f8f2428b101de7c32cd8719362941c5f))

* Fixing FutureWarning ([`deef924`](https://github.com/BAMresearch/McSAS3/commit/deef924ef0dc62dae9ad624fd82bfdd68a589280))

* addressing FutureWarning error ([`a84f907`](https://github.com/BAMresearch/McSAS3/commit/a84f907775713f31564d0533ceb836f7d27ce8bc))

* Update README.rst ([`49f262f`](https://github.com/BAMresearch/McSAS3/commit/49f262f8715715645f013bbac9fb323548f2d5c5))

* Adding an option to adjust IEmin ([`b4d5d08`](https://github.com/BAMresearch/McSAS3/commit/b4d5d08798f935a29fdfabe1d7d9c5ea180601a1))

## v1.0.4-dev.3 (2023-06-28)

### Unknown Scope

* Addressing a FutureWarning ([`eb80404`](https://github.com/BAMresearch/McSAS3/commit/eb80404f7a922e1aa7129526e3bb5615658a58fb))

## v1.0.4-dev.1 (2023-06-02)

### Unknown Scope

* added an .env file to simplify execution from CLI ([`32e0a83`](https://github.com/BAMresearch/McSAS3/commit/32e0a8357392932953a1f768be819eb97dc2d435))

## v1.0.3 (2023-04-20)

### Bug fixes 

* McHDF: Add info output for a failing key/value pair ([`b301c36`](https://github.com/BAMresearch/McSAS3/commit/b301c36878b5f42bd81bfb49857003e09fd0a234))

### Documentation 

* readme: Project URLs updated ([`6fb4d42`](https://github.com/BAMresearch/McSAS3/commit/6fb4d426eac39082fc74adef3358166484ca46fa))

* index: placeholder removed ([`a6ee36f`](https://github.com/BAMresearch/McSAS3/commit/a6ee36f600f2490b85d4976d7cbdb45877a65870))

* general: config update ([`a164332`](https://github.com/BAMresearch/McSAS3/commit/a1643325b714dc8a0b6e5412323ff7f34242a06c))

### Refactoring 

* McHDF: add note ([`8c336b2`](https://github.com/BAMresearch/McSAS3/commit/8c336b2a656d6019b01eb63caf8b42dd53503318))

## v1.0.3-dev.12 (2023-03-24)

### Documentation 

* readme: updated install instruction ([`bb88244`](https://github.com/BAMresearch/McSAS3/commit/bb88244fb2271558d2bc94aeccbb23ad9510d214))

## v1.0.3-dev.9 (2023-03-23)

### Documentation 

* Changelog: moving to markdown format consistently ([`083d67e`](https://github.com/BAMresearch/McSAS3/commit/083d67e44da904e17b76bb19977386cb762d5f72))

## v1.0.3-dev.3 (2023-03-22)

### Documentation 

* readme: fix formatting ([`8030a9d`](https://github.com/BAMresearch/McSAS3/commit/8030a9dafecfbea72ed1b46ac90daedf5b083b39))

## v1.0.3-dev.2 (2023-03-21)

### Code style 

* Documentation: whitespace removed ([`ebab058`](https://github.com/BAMresearch/McSAS3/commit/ebab0589f5fadea9ca4a00b1fe867f4965884182))

## v1.0.3-dev.1 (2023-03-21)

### Documentation 

* changelog: markdown changelog in pckg manifest as well ([`4d2b1c6`](https://github.com/BAMresearch/McSAS3/commit/4d2b1c6528d986a6e671fe02244d643419bb3bc9))

## v1.0.2 (2023-03-21)

### Bug fixes 

* Documentation: case-sensitive GitHub Pages URL (2) ([`42352dc`](https://github.com/BAMresearch/McSAS3/commit/42352dc7031c6cf0828db921e1b770969b29fa00))

* Documentation: case-sensitive GitHub Pages URL ([`c7ba4b6`](https://github.com/BAMresearch/McSAS3/commit/c7ba4b676581cfeb55276d1e724141fbcc1c916c))

### Documentation 

* changelog: fix rendering by using myst_parser for markdown ([`2203914`](https://github.com/BAMresearch/McSAS3/commit/2203914b0b7191016e6bdc2591286eac4c7f54b3))

* General: Fix parameters documentation format ([`b680822`](https://github.com/BAMresearch/McSAS3/commit/b6808225a60312ac3e500c2b46580efdca54a4e8))

## v1.0.2-dev.3 (2023-03-21)

### Code style 

* General: fix long lines and other complaints of black formatter ([`554db3a`](https://github.com/BAMresearch/McSAS3/commit/554db3ad797bef94b1bd74a73f27364b231a2711))

* General: let isort keep empty lines before comment blocks ([`0f7faff`](https://github.com/BAMresearch/McSAS3/commit/0f7faffda03a8c48a7aeb6b9a1420904b6687be8))

* General: black reformat ([`3463776`](https://github.com/BAMresearch/McSAS3/commit/3463776cc20e824aa738afc0e85d4bea8f937817))

* General: whitespace fix and quoting normalization ([`b06e61b`](https://github.com/BAMresearch/McSAS3/commit/b06e61b851409a5d64024911b5d2c2694163fe23))

* formatter: exchanged blue by black which is more common ([`0187120`](https://github.com/BAMresearch/McSAS3/commit/0187120b55c01c41af47fc7ae6484a2f0c813f08))

* cli: applying isort and blue on toplevel cli scripts as well ([`190b6d9`](https://github.com/BAMresearch/McSAS3/commit/190b6d92432fba7ed383ede95b210107cecfdef7))

* tests: blue reformatter ([`65e37c9`](https://github.com/BAMresearch/McSAS3/commit/65e37c9dbcd4b0625347faa0a181fa159f80119c))

* tests: isort ([`760ba21`](https://github.com/BAMresearch/McSAS3/commit/760ba216f4a810526c516388791f7cfe5d2c1998))

* General: reformatting code with blue (a black variant) ([`1f09cb0`](https://github.com/BAMresearch/McSAS3/commit/1f09cb015fa6b1c6b6e6e94ec9c7125a94e12ff9))

### Refactoring 

* imports: sorted by isort ([`34dbe0e`](https://github.com/BAMresearch/McSAS3/commit/34dbe0e1b612b3884f8557f80617ee5868362177))

## v1.0.2-dev.2 (2023-03-20)

### Unknown Scope

* minor edit, triggering rebuild ([`f3c0522`](https://github.com/BAMresearch/McSAS3/commit/f3c0522f5f58f551fa84e771e8e293b98b2e098c))

## v1.0.2-dev.1 (2023-03-20)

### Bug fixes 

* Notebook: platform independent fixed with fontname ([`64fd823`](https://github.com/BAMresearch/McSAS3/commit/64fd8232f6e6552bf2fcd74e01387c850bdde894))

* Notebook: set DPI of plot graphs to have same size on all platforms ([`fef5d66`](https://github.com/BAMresearch/McSAS3/commit/fef5d663d8d0c04c469b044ad212e9c2b2e749a8))

### Documentation 

* *: set up autosummary ([`01eaf83`](https://github.com/BAMresearch/McSAS3/commit/01eaf835bd2b245090ff7153c5201150e14eee6f))

* readme: format fix ([`35af983`](https://github.com/BAMresearch/McSAS3/commit/35af983fd459a4b90ab8b7f6a840b43d7fd5b82c))

* syntax: fix syntax issues with sphinx ([`de2f5b7`](https://github.com/BAMresearch/McSAS3/commit/de2f5b7455fb73bcac1bb68fe076ea779374cabc))

* notebook: how to install missing packages ([`222197a`](https://github.com/BAMresearch/McSAS3/commit/222197ab29335b6a9c0e239cb8ed99120c2ea851))

### Refactoring 

* Package: applied cookiecutter template renderer (WIP) ([`5271ee5`](https://github.com/BAMresearch/McSAS3/commit/5271ee534970a751d170d90dd1ff41dbda7854d5))

* Notebook: use all available cores by default, finish earlier ([`7d49345`](https://github.com/BAMresearch/McSAS3/commit/7d49345e239f0bc2f8b8b437423ddff5b7cc3dda))

* Notebook: mcsasPath is just the parent dir ([`2ddfa90`](https://github.com/BAMresearch/McSAS3/commit/2ddfa90749489fd3d0b1f11fadc1471cb1cb7006))

* Notebook: disabled sasviewPath, having sasmodels from pypi install should be sufficient ([`fe32dd5`](https://github.com/BAMresearch/McSAS3/commit/fe32dd51e57b72a99aaf3f274c0139727025d659))

* example: whitespace removed from notebook ([`6a315fc`](https://github.com/BAMresearch/McSAS3/commit/6a315fc59883f97ea2cc522b5956e091cec62d97))

### Testing 

* GitHubAction: exclude testOptimizer on GitHub, also in template ([`0cdec4e`](https://github.com/BAMresearch/McSAS3/commit/0cdec4e959a34b118fa208da3dfaeddc1e363091))

* GitHubAction: Install latest sasmodels to newer than from pypi in tests/requirements.txt ([`03d1e8c`](https://github.com/BAMresearch/McSAS3/commit/03d1e8ce5cd060c7a297b4a770551b7b06f8e21d))

* GitHubAction: tox syntax fix ([`4bcf509`](https://github.com/BAMresearch/McSAS3/commit/4bcf509b2d66f545be95cc998499791d8b36baec))

* GitHubAction: exclude testOptimizer on GitHub ([`546a79c`](https://github.com/BAMresearch/McSAS3/commit/546a79c36f9638569a67738530ac395ab04e81a4))

* Notebook: test it but exclude from coverage ([`9835076`](https://github.com/BAMresearch/McSAS3/commit/98350769e2e804d03e054886fde221e3eeb6788a))

* Notebook: fix windows paths format to unix ones in cell outputs by cell metadata ([`d6ce157`](https://github.com/BAMresearch/McSAS3/commit/d6ce157447bb4ac8602960ed2bb0ee5c7d52e2a6))

* Notebook: make sure ipykernel and ipython is installed ([`42a1934`](https://github.com/BAMresearch/McSAS3/commit/42a193443de3166e8d4077913657f5869ba36501))

* osb: converted doctest to code block, wasn't complete, did not run ([`0eaf993`](https://github.com/BAMresearch/McSAS3/commit/0eaf993e0634248190b503720f1be72f21113b8e))

* Notebook: removed ipykernel spec, seems to break test runner on GitHub ([`ce443b0`](https://github.com/BAMresearch/McSAS3/commit/ce443b047dff09045e6caa324fc7401948641b0c))

* Notebook: config for testing notebooks ([`16e9626`](https://github.com/BAMresearch/McSAS3/commit/16e96269a744e489df9b84b294539374112cd9c7))

* Notebook: outputs added, for testing and illustration ([`5a86ebc`](https://github.com/BAMresearch/McSAS3/commit/5a86ebcc271333ab5872cc4db94f7bbeee46f922))

* Notebook: disable interactive prompt when testing ([`576dd68`](https://github.com/BAMresearch/McSAS3/commit/576dd683db718ebb99c0018f871f2a912df57bd8))

* Notebook: removed defunct (2D) code, makes tests fail, impossible to exclude from tests ([`c449ff7`](https://github.com/BAMresearch/McSAS3/commit/c449ff7aaa03896615a23a7ae79cfd367188f19a))

### Unknown Scope

* 1.0.0 ([`b7734b1`](https://github.com/BAMresearch/McSAS3/commit/b7734b1d6b24f73e5a825cb70458a8d1f3ce1192))

* HDF: use PurePosixPath for / separators on Windows ([`a1e7ce7`](https://github.com/BAMresearch/McSAS3/commit/a1e7ce7d3630564bb9d89b8f7f9312eab948b328))

* pytest config to suppress DeprecationWarnings ([`4bcc3ff`](https://github.com/BAMresearch/McSAS3/commit/4bcc3ff1f1da0f55e9aca4be5df69501a8ae4448))

* updated requirements for unit support ([`977415f`](https://github.com/BAMresearch/McSAS3/commit/977415f8810569202c44244ad4c4cc19ebc7080f))

* preparing for packaging ([`1cfd9f7`](https://github.com/BAMresearch/McSAS3/commit/1cfd9f76ebb57bab5ee7e362424e1944501cfbfd))

* GH Action needs to install the pint module ([`daa8d3e`](https://github.com/BAMresearch/McSAS3/commit/daa8d3e95d618629ac8a7b8a3a09cc19d4b93da6))

* McHDF: store unit string along with the data, if provided ([`b8b3a6d`](https://github.com/BAMresearch/McSAS3/commit/b8b3a6d572500bded3b035382d6eeba0b24d6d52))

* McHDF: minor reformatting if condition ([`a724085`](https://github.com/BAMresearch/McSAS3/commit/a72408522c812377501d7e71bc912dd588918152))

* McHDF.storeKV: removed redundant *key* parameter ([`e8dece9`](https://github.com/BAMresearch/McSAS3/commit/e8dece9ea3115deb5256b757bbd32d899d54fb11))

* McHDF: using PurePath for hdf5 path, to work on Windows too (hopefully) ([`4d0ba84`](https://github.com/BAMresearch/McSAS3/commit/4d0ba84db539375276feb228fab5fffc5453c43f))

* McHDF: using PurePosixPath for hdf5 path not being filesystem related ([`74360ed`](https://github.com/BAMresearch/McSAS3/commit/74360ed6bdc1b07e0a2d1f75d84616cdc9a267f6))

* McHDF.storeKV: handle pandas.Timestamp ([`b5af524`](https://github.com/BAMresearch/McSAS3/commit/b5af52499e45142116e00cdb166bba7caf870d55))

* McHDF.storeKV: recursive traversal of hierachical maps in short ([`98c30e0`](https://github.com/BAMresearch/McSAS3/commit/98c30e06acebf310c2691e11430b2a7eb86e109f))

* cleaning up obsolete code remainings ([`74bdde6`](https://github.com/BAMresearch/McSAS3/commit/74bdde6b9a4d6222146c0a26644cbe405a0abd2a))

* McHDF refactored to composition instead of inheritance ([`926fad7`](https://github.com/BAMresearch/McSAS3/commit/926fad7fa5108edb9ac063c0b150c0b1a696dcbc))

* McHat: Print exception messages in subthreads ([`ee19ce4`](https://github.com/BAMresearch/McSAS3/commit/ee19ce4b86b4c2865a82c7b955378343a58896d1))

* mcopt: minor reformatting comments ([`d915990`](https://github.com/BAMresearch/McSAS3/commit/d91599088b1e545e5eb1a46fe5df0702f10ffe37))

* mcopt: sorted loadKeys same as storeKeys for comparability ([`d354d38`](https://github.com/BAMresearch/McSAS3/commit/d354d384236182c4cd73e34aaebe38a000710584))

* added Testing badge to readme ([`215f044`](https://github.com/BAMresearch/McSAS3/commit/215f044eb753328ce3a9bed3a91973d5b785ab0d))

* omit testOptimizer in testing workflow ([`4a634f7`](https://github.com/BAMresearch/McSAS3/commit/4a634f7b38011d158eeae29b4ea4986db618476c))

* disabled more tests in testing workflow ([`f4eb565`](https://github.com/BAMresearch/McSAS3/commit/f4eb5659702c860b0c61215d8cf09fea669b7717))

* run testing workflow with py310 only ([`39f9cd6`](https://github.com/BAMresearch/McSAS3/commit/39f9cd6fcc8beb3b769ecebfa4a00c0f2f73c8dc))

* Exclude computation extensive case in testing workflow ([`c9a57bb`](https://github.com/BAMresearch/McSAS3/commit/c9a57bbd761cea2cd42af30d411ffc181835fad3))

* Run testing workflow on Python 3.9 and 3.10 ([`f58385c`](https://github.com/BAMresearch/McSAS3/commit/f58385ca511f74c2f31b84ead860446d8b22220c))

* renamed test methods to run in certain order ([`75bfbfd`](https://github.com/BAMresearch/McSAS3/commit/75bfbfdbebac2a0a4b33e71c3b325004c4f719a9))

* Adjusting PYTHONPATH in testing workflow ([`b86aea1`](https://github.com/BAMresearch/McSAS3/commit/b86aea1e6ebca0a57ba8972204d73d762512d662))

* Adjusting PYTHONPATH in testing workflow ([`c346ebe`](https://github.com/BAMresearch/McSAS3/commit/c346ebede43fec2f5971545a142bb5023c78f863))

* Adjusting PYTHONPATH in testing workflow ([`1e9ca50`](https://github.com/BAMresearch/McSAS3/commit/1e9ca50dd15be869f5a1afac3652ee809b0cba68))

* Adjusting PYTHONPATH in testing workflow ([`dcfe6a1`](https://github.com/BAMresearch/McSAS3/commit/dcfe6a19651e937de650a115beb069fdbb285c40))

* reenabled time-consuming apt update in testing workflow ([`26417ca`](https://github.com/BAMresearch/McSAS3/commit/26417ca7c2c1c8f54bfefdbf52fad77c2228a79f))

* forgot sasmodels repo path in testing workflow ([`254e811`](https://github.com/BAMresearch/McSAS3/commit/254e811c995d179c45d3640e3eeddad45b3b00c6))

* more info on dir structure in testing workflow ([`a09e373`](https://github.com/BAMresearch/McSAS3/commit/a09e373155470aaf85d79c3adfbf4bb7c84b6b2e))

* Python 3.10 in testing workflow ([`05fb6cd`](https://github.com/BAMresearch/McSAS3/commit/05fb6cd9c7766e58514e3d2a94a7234fc505f080))

* Python 3.10 in testing workflow ([`50be71e`](https://github.com/BAMresearch/McSAS3/commit/50be71e457a8b4c6651f3ee25d387d2c99156db8))

* do not test sasmodels in testing workflow ([`1ab0dd1`](https://github.com/BAMresearch/McSAS3/commit/1ab0dd1e50cff1a0e85f4d7f727d7be6e37b223a))

* missing python module added to testing workflow ([`d60ad6e`](https://github.com/BAMresearch/McSAS3/commit/d60ad6e7125dcdfa8654c72a78ee2c8d793f027a))

* Looking for possibly existing .h5 file from previous tests ([`ed1cea1`](https://github.com/BAMresearch/McSAS3/commit/ed1cea17afc787c4371db946bcf37c7bbe471ea2))

* missing python module added to testing workflow ([`669f094`](https://github.com/BAMresearch/McSAS3/commit/669f094ebea5b6cb7a918741470d2d2fae422379))

* figure out dir structure in testing workflow ([`3c651bf`](https://github.com/BAMresearch/McSAS3/commit/3c651bf65d2a312a9e171dcb9099deeaad430f77))

* fix syntax err in testing workflow ([`8a8e871`](https://github.com/BAMresearch/McSAS3/commit/8a8e871d4a7b6fbe64908df2a61a549fe1039dc9))

* fix syntax err in testing workflow ([`6bc078d`](https://github.com/BAMresearch/McSAS3/commit/6bc078d072ca1e0275a7003708e992283eac51e3))

* updated testing workflow ([`b154123`](https://github.com/BAMresearch/McSAS3/commit/b1541234b25edecbbd971150d5cc4d99cd48f069))

* GitHub Action workflow for testing with sasmodels ([`b97fab8`](https://github.com/BAMresearch/McSAS3/commit/b97fab83ff2861c604c6912ecaf88f65f83d2bd7))

* cli_runner: number of threads command line options ([`8f1b292`](https://github.com/BAMresearch/McSAS3/commit/8f1b292ad69e9e6931209a080b317a2e4e2bfb11))

* let git ignore macOS meta data ([`f386566`](https://github.com/BAMresearch/McSAS3/commit/f386566e410edb4279e53739fa3a98c492fe6a2d))

* py3 shabang to CLI scripts added ([`2d93049`](https://github.com/BAMresearch/McSAS3/commit/2d930491bd9211058539362d0b50ef7980ae2ea6))

## v1.0.0 (2023-01-04)

### Unknown Scope

* Finished typing. Modified tests 2 run concurrently ([`a47b993`](https://github.com/BAMresearch/McSAS3/commit/a47b993a191a7504c8505d8a42dd43cddcd2ca48))

* Added type hints and reran unit tests. ([`617c44b`](https://github.com/BAMresearch/McSAS3/commit/617c44bb9fde6eeb2828c05895cb321b663bc2a0))

* Update README.md ([`a35bffe`](https://github.com/BAMresearch/McSAS3/commit/a35bffec23e87ba0eec80ca7b6b259f073bc6b05))

* formatting ([`5905566`](https://github.com/BAMresearch/McSAS3/commit/59055665fc978e60c68550b8c6b91495a6d4578a))

* fixed for SasModel's intensity - abs scaling works ([`b70a2ed`](https://github.com/BAMresearch/McSAS3/commit/b70a2eddc224a791af8652ca87891a4f6047894b))

* Update mcsas3_cli_runner.py ([`e4199c9`](https://github.com/BAMresearch/McSAS3/commit/e4199c9c85965d0638ce0c7f4621b3cbb93e6b5d))

* Correct arguments description in mcsas3_cli_runner.py ([`79b3523`](https://github.com/BAMresearch/McSAS3/commit/79b3523f9764352992d83eba0de1eb0e9ff2ad73))

* new ignore. ([`d98e2d5`](https://github.com/BAMresearch/McSAS3/commit/d98e2d5f93a504f440d3284bc71a372259ae41d3))

* Updates to fix loading from McSAS3 result ([`7eb8bea`](https://github.com/BAMresearch/McSAS3/commit/7eb8bea6afe7a7a41fefc57ef648e1f0229a75be))

* bugfixes to omitQRanges functionality ([`e72f66e`](https://github.com/BAMresearch/McSAS3/commit/e72f66e6058f3887cc418e7269935de516c38048))

* better coding in mcAnalysis. ([`1181015`](https://github.com/BAMresearch/McSAS3/commit/118101569b36e32781a1414ef082f8e681e82986))

* improved robustness in message formatting ([`cef9ace`](https://github.com/BAMresearch/McSAS3/commit/cef9ace384366bbd9e39a6ac695f2318502c56ba))

* Allowing omission of Q ranges in data read. ([`9cb263f`](https://github.com/BAMresearch/McSAS3/commit/9cb263f53d619ece0d1efa27b8084895c48e59aa))

* basic code cleanup. ([`bafdfc6`](https://github.com/BAMresearch/McSAS3/commit/bafdfc697fb206f9af42ef14611e89bdeb4054f8))

* small fix ([`ef8da6c`](https://github.com/BAMresearch/McSAS3/commit/ef8da6c6bd57b48a2f5033c29db860941183e615))

* Changed input args for better multi-opt behaviour ([`d612b71`](https://github.com/BAMresearch/McSAS3/commit/d612b71ed9c0485786fea94ac399423c05e6ecb5))

* typo. ([`3b56ccd`](https://github.com/BAMresearch/McSAS3/commit/3b56ccd28e67d40baf2e19290908a6bb0a42d98b))

* trying to fix ProductKernel scaling ([`7694700`](https://github.com/BAMresearch/McSAS3/commit/7694700a62cbf822e8f54877cba6dda89b6dcd0c))

* added note about installing tinycc to get sasmodels working ([`63428e7`](https://github.com/BAMresearch/McSAS3/commit/63428e76efffaa3ed831031c26c6b35862d03bb1))

* allow extended sasmodels (e.g. sphere@hardsphere) ([`395f841`](https://github.com/BAMresearch/McSAS3/commit/395f841a696f17675660851db4198cb55b06e61c))

* adding resultIndex to the lot for storing ([`22ccf60`](https://github.com/BAMresearch/McSAS3/commit/22ccf6024c77fa4b3a7463ac455d09ae73d1a01c))

* debug ([`7575c49`](https://github.com/BAMresearch/McSAS3/commit/7575c492a88a1531b357e3f007d9b4098bcef493))

* Updates to OSB initial guesser. ([`8d72499`](https://github.com/BAMresearch/McSAS3/commit/8d724994312fc7638e9ed8fad17ba93bc8d65fe9))

* removed duplication of initial guess for least sq. ([`b5d7fab`](https://github.com/BAMresearch/McSAS3/commit/b5d7fab81d6697d36898293fd57a68c2d898eb46))

* Allow McSAS to store its state in the dataFile ([`1a78994`](https://github.com/BAMresearch/McSAS3/commit/1a789942cf34068192b77d8fda5dc410a98c05ab))

* Update README.md ([`bb8e7cc`](https://github.com/BAMresearch/McSAS3/commit/bb8e7cc0895b6853ab5f42a47e3e1638661d107a))

* Update README.md ([`a8683b4`](https://github.com/BAMresearch/McSAS3/commit/a8683b466c7fef1dab4cad392ba2686591f9f46d))

* Update README.md ([`503c9ab`](https://github.com/BAMresearch/McSAS3/commit/503c9abcbda49f487ebf0f19ae57680d23da0c56))

* Update README.md ([`6bdfdd7`](https://github.com/BAMresearch/McSAS3/commit/6bdfdd70634fc4475dc8059bd94a89fa1b64bad1))

* assuring initial guess for scaling is in bounds ([`f3a0deb`](https://github.com/BAMresearch/McSAS3/commit/f3a0deb394634dd2e4a90d5b43fea78160d4fc62))

* bugfixes and cleanup of tests ([`146713f`](https://github.com/BAMresearch/McSAS3/commit/146713fffd3829841db3dfc9f6542f33891ccc53))

* Cleanup ([`c3a74b5`](https://github.com/BAMresearch/McSAS3/commit/c3a74b58d9a4bbdd6948cd03b01f54f7e2e700af))

* bugfix ([`ac313c7`](https://github.com/BAMresearch/McSAS3/commit/ac313c7207214b1f28b60f5101c8eb291f07adce))

* Added auto-range option for sphere radii ([`d854dfd`](https://github.com/BAMresearch/McSAS3/commit/d854dfdc9b5d0faa3461c158f5fd03832501a2af))

* bugfix ([`de6344f`](https://github.com/BAMresearch/McSAS3/commit/de6344f7abf53957aabd1a21f4e052cb534b2443))

* now also histograms and plots from the commandline ([`8e2f3db`](https://github.com/BAMresearch/McSAS3/commit/8e2f3db3cda03ff71041806bd8221e8565b1f69e))

* adding a cli- histogrammer.. untested ([`cb2ca91`](https://github.com/BAMresearch/McSAS3/commit/cb2ca915d1fb94fe12d26fe38175d089603c8892))

* conversion factor, SLD input in 1e-6 1/A^2 for abs ([`a9b9501`](https://github.com/BAMresearch/McSAS3/commit/a9b950189721dc5b624bc732cafdaeae602768a8))

* changes to set the SLDs and other static pars ([`52fbabe`](https://github.com/BAMresearch/McSAS3/commit/52fbabebe0e4399394a3c60e8c1e717573035c84))

* intermediate fixes ([`50e4cd9`](https://github.com/BAMresearch/McSAS3/commit/50e4cd947c4847313ebeb794c209aae210c39184))

* Setting up a command-line runner for McSAS ([`fc0bf5d`](https://github.com/BAMresearch/McSAS3/commit/fc0bf5d247fb11fa73b506e5bc88616fde4db108))

* adding a standard sphere model... ([`d0d267c`](https://github.com/BAMresearch/McSAS3/commit/d0d267c0f8105301e1def2be4acc9c0f8316dbbd))

* added a test for development ([`1fada73`](https://github.com/BAMresearch/McSAS3/commit/1fada73e5273f84eaa932a864d54f6a74bd5c0f6))

* Added GPLv3 license ([`467bbde`](https://github.com/BAMresearch/McSAS3/commit/467bbde6a077c1922d86eba68ce4326b480a2e74))

* Now works with Python 3.9 ([`8fd2e40`](https://github.com/BAMresearch/McSAS3/commit/8fd2e40d31af14ae34f50e4fb4f931de7fcbb6b1))

* Adapted to changes in HDF5 loading ([`0b24393`](https://github.com/BAMresearch/McSAS3/commit/0b243937d77b427994fbcfb9f5328e011ce47042))

* updated mcmodel to deal with the string-type storage ([`d9443a4`](https://github.com/BAMresearch/McSAS3/commit/d9443a49f1d05f0f16f22c94f11812bdbbfdcbe1))

* mcmodel: bytes->string conversion fix when loading data ([`78651a7`](https://github.com/BAMresearch/McSAS3/commit/78651a7a20aac308f8ceab5812b17d91044f92c2))

* examples.minimal: do not ask for the mcsas3 path, error-prone ([`256719e`](https://github.com/BAMresearch/McSAS3/commit/256719efd22ed71e16f2b3565903776dc42ea527))

* examples.minimal: fixed&tested for macOS as well, detecting OS ([`797c4a6`](https://github.com/BAMresearch/McSAS3/commit/797c4a66f389a57c5ace612e66ad2b424a98f221))

* examples.minimal: usability fix ([`d5a56b9`](https://github.com/BAMresearch/McSAS3/commit/d5a56b9cc56ae6d7f27e52584ae40bdec258b95f))

* examples.minimal: added cells for using prev. installed sasview on Windows ([`799e1a6`](https://github.com/BAMresearch/McSAS3/commit/799e1a6d1755cc020e6be66324e3ab0ee936f7d6))

* updated structure drawing, made in draw.io ([`a0f2cd1`](https://github.com/BAMresearch/McSAS3/commit/a0f2cd1d2aa1bbd4dfb5d43364129b128261ff29))

* Fixed scaling issue in simulated model version ([`c3988a6`](https://github.com/BAMresearch/McSAS3/commit/c3988a6aad1afa3fa8197a9854a11b63b174c665))

* Added an old drawing of the interdependency between the modules ([`a2c29a2`](https://github.com/BAMresearch/McSAS3/commit/a2c29a25aaf6529fee56b28c78250074521f470e))

* New example notebooks ([`69b1ce0`](https://github.com/BAMresearch/McSAS3/commit/69b1ce089a271d8fd0486aaeaf3bf77f50e95f6f))

* fixed bug in test ([`e0dc95b`](https://github.com/BAMresearch/McSAS3/commit/e0dc95b7bcbf363699a41a537a22c93261e94d1e))

* Adding test data ([`64162e8`](https://github.com/BAMresearch/McSAS3/commit/64162e88df3678a3964d8b11630f571523f28e16))

* Absolute units implemented. ([`356d4a4`](https://github.com/BAMresearch/McSAS3/commit/356d4a4d8a22047b782676f1aec1aa155aed8cc1))

* Resetting state and tracking optimization progress ([`67dbd0a`](https://github.com/BAMresearch/McSAS3/commit/67dbd0af86145d6217c2f7ebc5caa4a7bc3e43d7))

* Resetting state in McData ([`72b657d`](https://github.com/BAMresearch/McSAS3/commit/72b657d10c1cdb3173af1fb9aa32bb9dca13fcfc))

* Ensure resetting state ([`e1f948e`](https://github.com/BAMresearch/McSAS3/commit/e1f948ee9a00017ff68369591c316e4d63f16890))

* Adding a test to debug the histogramming population statistics.. ([`21565cc`](https://github.com/BAMresearch/McSAS3/commit/21565ccc96006ca99f3b58ca924e30e4df85f609))

* Ensuring reset between optimizations ([`4015f5a`](https://github.com/BAMresearch/McSAS3/commit/4015f5af2102e4bdee26a357909c6a459955ed95))

* test commit ([`313ef14`](https://github.com/BAMresearch/McSAS3/commit/313ef148d9043cc434ed9f78f7a8eb76b33ece96))

* updating in McPlot, nothing functional yet. ([`2cb8a46`](https://github.com/BAMresearch/McSAS3/commit/2cb8a4695f33e3ab690885be4ab96bea119972e0))

* empty mcPlot class to hold plotter functions . ([`2bc7275`](https://github.com/BAMresearch/McSAS3/commit/2bc7275eea2149d4eaeb6bdcf395aba05256e61a))

* updated sim model to allow for multiprocessing to work (i.e taken out dictionary from staticParameters, replacing by single arrays) ([`941964c`](https://github.com/BAMresearch/McSAS3/commit/941964c80a8490fa5cc806f30ac298d7b1809535))

* Updates to string formatting ([`3c56bee`](https://github.com/BAMresearch/McSAS3/commit/3c56bee20a0e75fce8c99858b0eb0cf1f0fc9ad0))

* Fixes for the sim-based fitting ([`259eb5b`](https://github.com/BAMresearch/McSAS3/commit/259eb5bd780aff34dbcd9a2f132177f7589f831f))

* Moved calcModelIV to mcmodel. Now everything I should have to change is in mcmodel.. ([`695dab5`](https://github.com/BAMresearch/McSAS3/commit/695dab5894e6dd1b4b270d453f9d3b9c1016718c))

* More tests and a 2D class. ([`ccd22d9`](https://github.com/BAMresearch/McSAS3/commit/ccd22d964538bb0de31e6cc2a174f27fdcb8173f))

* mcAnalysis can create a small text block stating the histogram modes.. ([`3cc59e0`](https://github.com/BAMresearch/McSAS3/commit/3cc59e04c804f8967bf0dc586a7a8011da334773))

* fixes and implemented a reconstruct2D function in the McData2D class to turn the list of model intensities back into 2D form matching the clipped data. ([`a6c08eb`](https://github.com/BAMresearch/McSAS3/commit/a6c08eb52b6f18ba3f0d726e007797ccbedebb08))

* 2D data class largely written (still need additions for returning fitted data to shape of original), starting to fix histogram storage. ([`fe73d9c`](https://github.com/BAMresearch/McSAS3/commit/fe73d9cd9d00eced5f7607e2e1bffd7700e4e8a6))

* universal nexus data loader for 1D and 2D ([`3f0faa5`](https://github.com/BAMresearch/McSAS3/commit/3f0faa5dc2bedb1884fbf9b611efc84d9e5f6e43))

* Updated HDF5 segment to allow adaptation of the entry point into the NeXus structure. ([`e0c1fca`](https://github.com/BAMresearch/McSAS3/commit/e0c1fca35f4760577af7640ef568ea9941582162))

* minor updates ([`b20ef4a`](https://github.com/BAMresearch/McSAS3/commit/b20ef4a104d63e6c105aa87fda26cb160ed63c4c))

* added test cases for nexus ([`bd68ddc`](https://github.com/BAMresearch/McSAS3/commit/bd68ddc350fa9e63415cc524bed880847cce150b))

* Added test case for loading from NXsas files. improved state-restore unit test for csv data loader. ([`094a7fa`](https://github.com/BAMresearch/McSAS3/commit/094a7fa31fb162a976161cfe8bc36b2ed7af132b))

* McData can now load 1D data ffrom NeXus / DAWN processing output files. ([`cba7dec`](https://github.com/BAMresearch/McSAS3/commit/cba7dec0865f9c20592b08f81902461293532204))

* Updated directory structure, and updates to McData to restore state for file-loaded objects. Tests still needed for pandas-loaded data - state-restore. ([`55f57f6`](https://github.com/BAMresearch/McSAS3/commit/55f57f60c1ff002c209ce2994f46a04838f5cbbb))

* resolved an issue with HDF5 writing, occurring when rehistogramming. ([`592181f`](https://github.com/BAMresearch/McSAS3/commit/592181f31c5c9cac20b94488f7e9c0f25cbc2b4f))

* Added tests and updated minimal notebook example... ([`29796da`](https://github.com/BAMresearch/McSAS3/commit/29796da4851493eae6ff8cee25849266872e3705))

* new notebook, and an integral test for a sphere example ([`6f3dc5c`](https://github.com/BAMresearch/McSAS3/commit/6f3dc5c54cd6b0d0eb199b5150b487d414c83cf9))

* Added test cases ([`9316155`](https://github.com/BAMresearch/McSAS3/commit/9316155d03909d0e641514adc1830f18d23d9555))

* Updates and reformatting, also added unit tests for McData. McData can clip and rebin input data from either a dataframe, pdh file or csv file. NeXus support will come. ([`bccfb51`](https://github.com/BAMresearch/McSAS3/commit/bccfb51c9004ec29ad62cb4a5939a4775f6560e2))

* Initial setup of a McData object. This can do binning and clipping if necessary. ([`acef444`](https://github.com/BAMresearch/McSAS3/commit/acef444bdf1a3d7e3b75dde3686b4bcb441520f5))

* Minor change to make it run in a current version of Python (3.7). ([`8ebc112`](https://github.com/BAMresearch/McSAS3/commit/8ebc11213f3fb7afad411aaebbb894b1b2f68e37))

* fixed access modes in h5py.File() calls ([`ac7f30a`](https://github.com/BAMresearch/McSAS3/commit/ac7f30a50a2fd99fcc4c8f795018bbb0adbf2a61))

* minimal NB: fixed syntax for DataFrame constructor ([`760b58d`](https://github.com/BAMresearch/McSAS3/commit/760b58d0039579bc79fcd592f1b5c319b96fab1d))

* McHat: show more runtime info in analysis summary output line ([`5ca8c39`](https://github.com/BAMresearch/McSAS3/commit/5ca8c399476e8ecb12b9c2f12154088ba28ed44d))

* updated minimal McSAS3 example with gaussian coil BSA data ([`dcda0ee`](https://github.com/BAMresearch/McSAS3/commit/dcda0eebba840077a721e23783cd870d24f03f87))

* McCore: divide volumes by nContribs too, otherwise totalValue equals nContrib ([`bcb884e`](https://github.com/BAMresearch/McSAS3/commit/bcb884ee860a04d44478face965247976f0d6d9b))

* McModel: allow seed to be None, required for multiple reps; handle None value with HDF5 ([`5cf5156`](https://github.com/BAMresearch/McSAS3/commit/5cf51565fe6a6f44a7d91b6b593f7b4f39e9ee23))

* McHDF: fixed unicode handling for other parameter names than *radius* ([`d4f6506`](https://github.com/BAMresearch/McSAS3/commit/d4f65063d260af177069e4a842fdeccfba402928))

* McHat: multiprocessing works ([`17c34ee`](https://github.com/BAMresearch/McSAS3/commit/17c34eed979b7583d3b419fc5b9cfb4695023ebd))

* McCore: disabled consistence test for loaded results from HDF5 ([`d73b07b`](https://github.com/BAMresearch/McSAS3/commit/d73b07b94a8342f727ff1e9975c25b733a620cba))

* McHat.runOnce() for a single repetition ([`23f0c5e`](https://github.com/BAMresearch/McSAS3/commit/23f0c5e65ebeb56129024b4f14ff3ef163b60f9d))

* McHDF: fixed warnings about deprecated h5py API ([`33a9163`](https://github.com/BAMresearch/McSAS3/commit/33a9163a74db0cc7ba994b3b19f13dd9e8c7ccd8))

* minimal NB: calc multiple repetitions and plot distrib. histograms ([`bd16bce`](https://github.com/BAMresearch/McSAS3/commit/bd16bce65f9753cfd6355dec0d2a7a0ff24adae8))

* McModel: also store/load modelDType to grab the correct model dll later on ([`b75ac2a`](https://github.com/BAMresearch/McSAS3/commit/b75ac2a6b481f1fc1565c4a28b49d9739635ac0c))

* minor whitespace fixes ([`3a72f3a`](https://github.com/BAMresearch/McSAS3/commit/3a72f3a9fa44f7c8da316c2e3d4b31d94a1a0772))

* McModel.fillParameterSet() renamed to resetParameterSet reflects the use case better ([`fc85125`](https://github.com/BAMresearch/McSAS3/commit/fc85125c350b95f0e0e8ec9abe88504f47f8e0d0))

* McAnalysis.debugPlot(): forward custom keyword args to plotting ([`af753ac`](https://github.com/BAMresearch/McSAS3/commit/af753acd8dde1012d374f84b8c9c1ebbe87972a0))

* minor whitespace fixes ([`7d44c3e`](https://github.com/BAMresearch/McSAS3/commit/7d44c3eef3e2916f329b36fc28f705005e85c3e6))

* osb: using TNC minimizer by default ([`3f3955a`](https://github.com/BAMresearch/McSAS3/commit/3f3955a2d9e2d871e35990bc81c282666e0f63f4))

* McModelHistogrammer: missing assertion on histRange.nBin added ([`3ce9d96`](https://github.com/BAMresearch/McSAS3/commit/3ce9d96be2068cb24f7a332009ff5eac06909e94))

* mcmodel: using fast mode (single precision) for models from Sasview by default ([`a6de348`](https://github.com/BAMresearch/McSAS3/commit/a6de348dcf61d11470c0848e57e4f71cbf5f5b69))

* let git ignore results.h5 from minimal jupyter notebook ([`09bd3b1`](https://github.com/BAMresearch/McSAS3/commit/09bd3b1d75c438478c08665ddc0638f8458555e1))

* minimal.ipynb: minor formatting ([`e165046`](https://github.com/BAMresearch/McSAS3/commit/e16504696c212778f3b8dfebcd638d1f8555b751))

* removed debug output ([`f3c3c23`](https://github.com/BAMresearch/McSAS3/commit/f3c3c238df4ab46d7b958384cb2aeac1f9965124))

* updated minimal jupyter notebook example ([`7358888`](https://github.com/BAMresearch/McSAS3/commit/7358888d770b21f213001d4a17e6490255afa4a9))

* Fixes. Now checked against the old McSAS output. ([`c5ebf01`](https://github.com/BAMresearch/McSAS3/commit/c5ebf01729c30aeb889379a6a5546c539d733113))

* Updates to: 1) store the result in a more NeXus-compatible location, and 2) work with the updated sasmodels library method for volume calculation. ([`77f7191`](https://github.com/BAMresearch/McSAS3/commit/77f719127e1995e68250fe5afe14d02dac4d4126))

* Put the core loading code in its own method. ([`5c3cc0d`](https://github.com/BAMresearch/McSAS3/commit/5c3cc0d5affa0010adae600f7f23e418e2ec4a88))

* McAnalysis now draws solely from a McCore instance, allowing further analysis (observability, etc.) to take place easily. ([`6de7642`](https://github.com/BAMresearch/McSAS3/commit/6de76421a3642c68ccb7aea6cbe7621bcd91785d))

* Model intensity also averaged now, finalizing the basic functionality. For further averaging and calculation of observability limits, however, a McCore instance must be recreated. This will probably require a consistent data model to be used, so we need to work on getting McSAS3 to work with the SasData class of SasView first. Another item on the agenda is to get McHat running, so we can exploit multiprocessing... That shouldn't be too hard. ([`cafe7c2`](https://github.com/BAMresearch/McSAS3/commit/cafe7c2ce0c25ae51b5547cbef43049a6d7b8e91))

* Optimization parameters are now also averaged... ([`dd26be8`](https://github.com/BAMresearch/McSAS3/commit/dd26be841bdf79aca062ddb5fc67f25fb1fd43f2))

* minor bugfix ([`2dd455c`](https://github.com/BAMresearch/McSAS3/commit/2dd455ced2d76506b3591201ef8d2e44bf3739c4))

* McAnalysis now also averages histograms and can do a debugPlot of the histograms. Scaling, observability, and cumulative distribution function not yet implemented ([`7b2464d`](https://github.com/BAMresearch/McSAS3/commit/7b2464df91054c766f4a5c9a05dc33d7f711edb3))

* McAnalysis now runs the histogrammer for every repetition and histogram range, and averages the modes from all the repetitions for each range. ([`a815735`](https://github.com/BAMresearch/McSAS3/commit/a81573557c8e72786e2b45c6b986e3becd412360))

* McModelHistogrammer now can store histogramming results of individual repetitions. ([`41ec032`](https://github.com/BAMresearch/McSAS3/commit/41ec032511f9d91646fe45ded8ead1357c2a48b9))

* WIP: overall analysis of the results from multiple repetitions. ([`f87dbf4`](https://github.com/BAMresearch/McSAS3/commit/f87dbf4333abcec6701b53caed0fa764f147d1c9))

* adding separate histogramming functions, need to be provided a model instance and histogramming ranges. ([`533a7f6`](https://github.com/BAMresearch/McSAS3/commit/533a7f641279a8580515c4bf97acae4357faffd2))

* nRep has moved to McHat. ([`4b28021`](https://github.com/BAMresearch/McSAS3/commit/4b28021dc3ed9ee61bf81daeaeec62b4e91e5ceb))

* minimal NB ex: error cases with SASview models discussed ([`e9dcb4c`](https://github.com/BAMresearch/McSAS3/commit/e9dcb4c9d293f2c97dfcacb452afd8684a5427af))

* let git ignore any sasmodels folder in here ([`58b1840`](https://github.com/BAMresearch/McSAS3/commit/58b18402dbb32e821216a8cabd5d343e411c6346))

* minimal jupyter NB example: notes for Windows added ([`302dbf9`](https://github.com/BAMresearch/McSAS3/commit/302dbf9a175e90a641a978780dfc1262a31780b3))

* updated gitignore ([`9aac479`](https://github.com/BAMresearch/McSAS3/commit/9aac47945a834604a51e09dae6268f056b4748ce))

* update minimal jupyter NB example ([`8f1c053`](https://github.com/BAMresearch/McSAS3/commit/8f1c0534fc94cabf9e9dd4b86db0b8a881df31ce))

* allow sasview model dtype to be set from outside ([`a5aad7c`](https://github.com/BAMresearch/McSAS3/commit/a5aad7c94628c5ec0f171de5cfb004bbdfc93932))

* Bugfix and start on new parent function to do multiple runs. ([`3b4b334`](https://github.com/BAMresearch/McSAS3/commit/3b4b3347cca096790b1317bcb6e800efbc07c72c))

* Cleanup and modifying parameter names to be more descriptive. Loading now working. ([`af5b243`](https://github.com/BAMresearch/McSAS3/commit/af5b243226f85ca446f0efaf31b553582708c70b))

* Loading works for McModel... onwards to McOpt ([`2b8dbed`](https://github.com/BAMresearch/McSAS3/commit/2b8dbed1bb07b3e65c85063596a3425422df8646))

* sasmodels integrated ([`2068fc5`](https://github.com/BAMresearch/McSAS3/commit/2068fc50130139807f7a4515c5d47bdd3b8594e4))

* HDF storage works, next step is loading the configuration and model parameters from an HDF5 file. ([`8054a11`](https://github.com/BAMresearch/McSAS3/commit/8054a1168f7d17e5a7a36d02c45bf654b64061d7))

* storing of datasets and options implemented and tested. ([`0adcb45`](https://github.com/BAMresearch/McSAS3/commit/0adcb458be32d8eba3bf7224ce43ca25ddbe398c))

* Initial functions set up for supporting storing and loading of settings and repetitions. ([`fed7b59`](https://github.com/BAMresearch/McSAS3/commit/fed7b59d73210db6352203935540314b5eb10816))

* Minor fixes. ([`dcbc1cd`](https://github.com/BAMresearch/McSAS3/commit/dcbc1cd01e6d4b3b80e73273849560006448cb2f))

* added minimal jupyter script for demo ([`7cb85cb`](https://github.com/BAMresearch/McSAS3/commit/7cb85cb555efd04e5e1800317fb7b6145202269b))

* static parameters weren't always applied. Ensuring that this is the case now. ([`381c7fe`](https://github.com/BAMresearch/McSAS3/commit/381c7fe11ee4286bc274ef3e93bf6020905d5412))

* updated ignore ([`1ce88aa`](https://github.com/BAMresearch/McSAS3/commit/1ce88aa1fbc1645fe54e59715bd80b16bcdd2f53))

* Updated gitignore ([`9c3e281`](https://github.com/BAMresearch/McSAS3/commit/9c3e281f9926f7d3c20f5e4b657210f7984bf0d0))

* Offload MC functions into their own files ([`584bee8`](https://github.com/BAMresearch/McSAS3/commit/584bee8e233b6a3155cd795f1605843a94c27c2d))

* added gitignore ([`a14e52e`](https://github.com/BAMresearch/McSAS3/commit/a14e52e02f76245ab42b8b2a5c8628a9e6989129))

* Initial commit, mind the mess! ([`7df539e`](https://github.com/BAMresearch/McSAS3/commit/7df539e33481d84bfdab979f153cf4fd2b7531ac))

* README.md edited online with Bitbucket ([`3029cda`](https://github.com/BAMresearch/McSAS3/commit/3029cda8e9baf14fd1eea6ceca26e32a989c4666))

* Initial commit ([`db2937c`](https://github.com/BAMresearch/McSAS3/commit/db2937c11323ef565d4b1edd2e6a73aba36eb40d))
