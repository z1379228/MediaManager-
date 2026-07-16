"""Pinned integrity metadata for MODs shipped with this core release."""

BUILTIN_PROVIDER_HASHES: dict[str, dict[str, str]] = {
    "direct-http": {
        "provider.py": "cd8473f4e323278cbd40ca16598268256918c86bb64a5176b470a141810a994a",
        "provider.json": "001b249260a75bb7f284b4cbc53b0d91a646a35d4dfc7027e3a273a757d448c7",
    },
    "ani-gamer": {
        "feature.json": "8007aeb21bcb58e3e22bee8fbd25174c2b35c84aaa89bb89fb8625a0d38b32bb",
        "group.json": "f5e35c014d1329162e18fbe089d03b2c5d884c03fa73b5540cc1a05bac32d7ac",
        "locales/en.json": "f8a86f68a092bc92e27b35852bfc0324f779632b28666981d53579c9dc3ec107",
        "locales/ja.json": "690c6598f5917816fd8c3ef129fb3320b70b8cc64b8659020c6ce351bcef37e3",
        "locales/zh-CN.json": "f325e7eb44543e4f863d279c654fe944d115239a2ba67dffff68448f01b98444",
        "locales/zh-TW.json": "ba2f3e7210bf6bb78ad62e75f5994d5e0587c8661a1120e30c4e55fe66ce957c",
        "site-matrix.json": "e8f81be39fa7c5b2e55205dd1c56b38d728362163c5c4729b5fad206edf82ea1",
    },
    "ani-gamer-offline": {
        "feature.json": "3a02e563cab84182ce821ec92409e7d82ed1b658e7dcb98caaf09f69fc1140ef",
    },
    "ani-gamer-search": {
        "provider.py": "8019a2f0ece26834e162b430bb4deceb7e6598fa5ad566be3a07e828bd115653",
        "provider.json": "ea87fe49c16e3a273afe28f7f17e85e69160fd6500b63a72897f1fecca72babe",
    },
    "ani-gamer-episodes": {
        "provider.py": "51b10c119fda766318738ba26b5dba08c0a7bdc1dcb08878d5604b3f5a2e2860",
        "provider.json": "9abb62a3379a4a7cbf3b306ff3c3405ebf9258b9f91edf0ac05126f26e570923",
    },
    "automation": {
        "feature.json": "47fe2b5f6277a064ae404b466819e4383b5928862698a4a0c7f44675ff144f4e",
        "policy.json": "3f73591d23b4b01f49abb2e9812710d23e07c8cd219d1e52f37715b22dca380f",
    },
    "media-convert": {
        "feature.json": "82ebdfa5d8b10c7fbab28166a0aa294f8ad85288e7b248b6ef272f05184d92cf",
        "presets.json": "b4f222a0fcf8e90a4333ac4d85c4aaa8da2ba2d88953031eaab6f8788bc4c076",
    },
    "media-ad-trim": {
        "feature.json": "41ed53afbcdba49d047133be164b51fdf6f27df77c6965d9f67eb6a387a13d8d",
    },
    "speech-to-text": {
        "adapter.json": "0d155d02eadc79b42abc12479bf5ceee79e3739b6bb43e20ea9d1ffc71403046",
        "feature.json": "e5d9222296dfe35e7b552bdb109d8d2d5dbe766a961e38e1ad562875289544ae",
    },
    "bilibili": {
        "danmaku_ass.py": "3f3d7c51af875bb8ba0d093215a182712db513f4676a2ae5c688afc8bf595041",
        "group.json": "a12066bee823d5a789719d62ba237f787a98a4e6752f469d10f39565473820eb",
        "locales/en.json": "991160c7930ec31a4ed6a2848b8a6cca43af1ed337c0f5b3eb9875121204feca",
        "locales/ja.json": "80dff59055ce21ee2dc1fe3102a9b90ee0836bb146bcf0990a3830e85ae8370e",
        "locales/zh-CN.json": "d95a930210405fa1b9948c746d21b3d27ce29d8ec794aa41960c61f4c8501342",
        "locales/zh-TW.json": "83d12ba5a053ca20daa8e10340ddabd92ba86a1c88584ac8ab67e3668d388428",
        "provider.py": "86cb4708bda3a7090509d192509b53fb5025a3dc40a2c50e7fb9aaf83849e3ce",
        "provider.json": "ebf0c166ce2e43479ab1f8f824b192ac9d36c40d519213b2cf336a1102a0800b",
        "site-matrix.json": "1b6a7ccd7f0ab52402d331b14e5aa89a1ed77f31f0befe968007cc888e0a5778",
    },
    "bilibili-search": {
        "provider.py": "f6af795067fca4306ec0030c7031b2e191eada3745851b7e41559b849da27115",
        "provider.json": "c275c393179fdc143c13251889acdabb5b67ae75d4c1b53f41387a2aa5e16a99",
    },
    "bilibili-danmaku": {
        "feature.json": "341085b84f205fb247fee7e1987aab0bb39116b31ceae62840995b8626d00198",
    },
    "generic-ytdlp": {
        "provider.py": "b7a87e87a88cd2fd35122d9f3a71381c9b77a1f1260cf62e6caaf6d0ef8b735b",
        "provider.json": "a84b1bf1dca22bcf3b947496accaf09fb69720644320dd99ca330fc283511bdf",
        "site-matrix.json": "282e35bc3cc5b9f627d33eec7287221cee9d6a46efa1214b0d31cba80173ddf6",
    },
    "instagram": {
        "feature.json": "fdfdbb20dea7fc0a5d33d2a5a9107003172a62b83c4efc5bd1799b9ee1796615",
        "group.json": "2c983755c789a5fedc7a407a60f6efee008e17f3024e416d5ed935fba2c5d2e5",
        "locales/en.json": "1329d6a38d9f653f953defef029aa7fb193ea223cef86c0567da8dea9aa1fd0f",
        "locales/ja.json": "67391950eba68bccc5c769ff465bee840b6f12f79b89848fa695b2a6d7cf2711",
        "locales/zh-CN.json": "7c226eb78befb80087d60f46034e5caaaf42d1cd556c0aaddf310231e3c9da92",
        "locales/zh-TW.json": "4cc08d1a9c1582da28f96f41390dee700e6d162d4808801f3c35b3aa5d6b81f0",
        "site-matrix.json": "f1f01690e4ecc8e2d414ad228436cd096dfa25e37d3d7dedc0aca481839747fd",
    },
    "instagram-page": {
        "feature.json": "c91cfb5a2d8a301578024d15b479c1d6b2499eb3c6b15ebf8bd1ae44100f4eed",
    },
    "instagram-export": {
        "feature.json": "658d8bddeeef4aec80bd8b15d42b0876a801f46fc40a331f792c7c99e1b21fa5",
    },
    "threads": {
        "feature.json": "174b0ca4e26a3617cec94c4baeccda9e527e53771c5f8cd21888bec377dbfbcd",
        "group.json": "53b627eed56b437801266efd8c2e459bfc155674ea673a525389d23c7d90d1d8",
        "locales/en.json": "7ecd0d0a8cd0d84c95d6875c26ffcf28c9cf797d278d39b4d3f18e6a579efb0f",
        "locales/ja.json": "a5861d4dd966313c25c8e1f113b57c3d173411e6db43a0ed81f1d4c861fed1c6",
        "locales/zh-CN.json": "842a01b95b130d9868998dc4b8d67302cd486e3893e57bcb9a2e3b95eaff948a",
        "locales/zh-TW.json": "687e6ce6f4474634401cb39013c069c71d1e7f10cbcfdac7528e2f55f246e46e",
        "site-matrix.json": "79f957365a7d291fb11a128c5ebdcbf1aa0d5e25a0572b09d27d50368a55382a",
    },
    "threads-page": {
        "feature.json": "82ce258c4c12f091fb6677b0ad67764c3bbc6a13de601f94b9f8a49a27ca623e",
    },
    "threads-export": {
        "feature.json": "6b4abd4df6e5dcc10cab1a08154147196a8fa23d811a11d47393eabbb474d252",
    },
    "twitter": {
        "feature.json": "5a111e5e21098f6a72b7812be08e9c5ee1f1aaaf2149e354538865738dc3d93f",
        "group.json": "b8053f2225fbfc53e9858295d9e0a1c0d33583303ea14db2e3565e2e2c0e4c73",
        "locales/en.json": "956c6b874e451fb09b58091f0aeb238daabad77e065d08b4439af174d1673d40",
        "locales/ja.json": "7e805bb83c88f42b0cf5f17f5638e60ab19d48e8f6d8d74bd32bc073c8242a1c",
        "locales/zh-CN.json": "47703164e9b1956d504f72b592b5449787486a80878b7ff53e03ccb2327b764b",
        "locales/zh-TW.json": "ac934890d0fa611130177d4b459ec3133f7ff5b309feadd6eb0b3ffcbb3727c5",
        "site-matrix.json": "d66027071e02a0db3768c531b651c86c1b2be20959ca94694fcf122a50aae33e",
    },
    "twitter-page": {
        "feature.json": "bddb81e2f00c226c981c672db00b0feb9f6fd79e206f58e81aeff99ef0178e2d",
    },
    "twitter-export": {
        "feature.json": "1b8f4ce2b1ced089bde5b8f7afc6f97228eb2f0168400e067743d46c292b873b",
    },
    "facebook": {
        "group.json": "8570bb0ae0709deb5b89234ff1d08bab3a12dccc4ab80e0c6bfbe50702d3f680",
        "locales/en.json": "ab31937b62985fc6ead0eaf09d9ebae4f1438effd067a195d3e08299357deb1b",
        "locales/ja.json": "bab55ed5c374427f441ad3a516cdf63989dd7c2be70460785d4181fc033fcf9a",
        "locales/zh-CN.json": "1ce4dc6264663c012f80384ad7698895330f71fb87ee734ebf462bab9acb3a72",
        "locales/zh-TW.json": "1bf1853980b013db3bde67ae4fa6a81e8f69608cc9486874770b220503c75d08",
        "provider.py": "7efc8c20b40e41c2a5a0bdb0aaebbfcc5346d686e5ac40354d744a9b08f9e43f",
        "provider.json": "b561dcce2a52090618604eb214046cb7894906c0dd7d308f607178be381ed1f7",
        "site-matrix.json": "d1d4d8e83e8e5a05603133f8a615f9a096a46ce2c1d9449d83fbd469649f6d94",
    },
    "mega": {
        "group.json": "c541dbc81ebbdca4f949ef66419acc0f0486c02a898bd53e472b5652b865e1b6",
        "locales/en.json": "3c9f3cce78437c0bf841d1de75ad392af9fe0c1ef50e1758548ce664d1b8a0c9",
        "locales/ja.json": "11415c166ee2a78818da12b7b91aae5606e23ec0a85c5c9f24b1c7a301d538c7",
        "locales/zh-CN.json": "323edbf13dff9347c81a7b5c207f62d5c4b4054fe55de6206a437d565129faf8",
        "locales/zh-TW.json": "ad832a830a86f8c8c671f3857725268e87715a48ea7952a1d13ae0dbb18397fc",
        "provider.py": "bfa5ff908083a63f153a2ca5eb77d0120c7cc956b9b7eff12b52613c528bfc8e",
        "provider.json": "21023fe910ac917504ac37cc18f32a618a48bda988bad4c2a4171e126c554513",
        "site-matrix.json": "96abf365969d51a5d66ac23598fa8fcc40a2cbbe6b848f7056e322311aa13fdd",
    },
    "youtube-player": {
        "provider.py": "972c899b078849b2497929d479bdeefda0b878a9f0d7d1320f0460b6942efaaa",
        "provider.json": "852e1a3cb06dd2f52d4e8c506ce0f8e448a7511014d35dde022aceac69aecd44",
    },
    "youtube-auto-split": {
        "provider.py": "654c6b416376c5c010f72c6c22e993cb408b61b74020e1e3f8bdb20fb37a66f1",
        "provider.json": "8814a26f73582fbfbbb60f037178486cbf8c2be256fef7a01e2a8ae86d71437b",
    },
    "youtube-similar": {
        "provider.py": "f1c01bc181b81fe2accacdd461a8e9ab604f1c16914be00bbcb747f333932fc4",
        "provider.json": "3c0d3b5d558562f16700d3508099489ba4249bb183612e56e94003e309ffbd45",
    },
    "youtube-recovery": {
        "provider.py": "a1e36b8eb22830214c848aab9663d85fe2f82d87ce3a048c1a79debaa56e57bd",
        "provider.json": "3a516b1f9fef365c8ecdb32489bbc5bf6e365b47dcf22f13c3b2eaa7c633825a",
    },
    "youtube-history": {
        "provider.py": "845a452dd78ec1c73ddc7e4a97ce5c8a21fae2e7465c0be555c2a47131a8b062",
        "provider.json": "245272699a641df727f3d67b09b42d2d2bad0d0f5ea00a4086700300bfe1800a",
    },
    "youtube-search": {
        "provider.py": "fbb4c9271212ea4e95d2d81c4cfd0958632ee284c9c945b6c797236d9bdb344e",
        "provider.json": "b021207faa764b58f65c660f3ebc8759236067f90f5b59249a6c507cdd906add",
    },
    "youtube": {
        "group.json": "73e2bd4a2806f7bc5875bd73ba5de850783d3c1ce143e5bc95add5f39283839e",
        "locales/en.json": "07ae9a731b2eedc93c925082091df97fa55d25e6ea7310504607fa7d2ac66a2a",
        "locales/ja.json": "02536cf0599ff5e866044db79812f8a147ee4775d6b019980246cf6bcd55f7ce",
        "locales/zh-CN.json": "aecb2c1652049bbc57280f4a70ab8e8912d635a7f7516b57c4a46ce7ed43472a",
        "locales/zh-TW.json": "6ab7e060426c53add0a1f9f552ff261572eb2c089d5d3d671c334958198e75b0",
        "provider.py": "c10299a295ea2a8c4cf035d725d83aee4b2b3763aaf66d86d4d6a22a06a0e65e",
        "provider.json": "77eaa8296c85bf59838fe4db517e79077f4bd56ff7176fec4b66e9ce20c7d97d",
        "site-matrix.json": "1ec046c1b7d6d3e631013d825c0b5478d10f912a3a5a99eb2a0f6785f619feaf",
    }
}

