"""Pinned integrity metadata for MODs shipped with this core release."""

BUILTIN_PROVIDER_HASHES: dict[str, dict[str, str]] = {
    "ani-gamer-search": {
        "provider.py": "16c49ab64198828754a762e65b86a1e22eb6be4293feb74d5dc5ea6168278884",
        "provider.json": "ea87fe49c16e3a273afe28f7f17e85e69160fd6500b63a72897f1fecca72babe",
    },
    "automation": {
        "feature.json": "47fe2b5f6277a064ae404b466819e4383b5928862698a4a0c7f44675ff144f4e",
        "policy.json": "3f73591d23b4b01f49abb2e9812710d23e07c8cd219d1e52f37715b22dca380f",
    },
    "media-convert": {
        "feature.json": "82ebdfa5d8b10c7fbab28166a0aa294f8ad85288e7b248b6ef272f05184d92cf",
        "presets.json": "5563fa10d9a3ef5bcf258596cb815be32620cab83c6a5c77ac8647818aab0724",
    },
    "speech-to-text": {
        "adapter.json": "0d155d02eadc79b42abc12479bf5ceee79e3739b6bb43e20ea9d1ffc71403046",
        "feature.json": "e5d9222296dfe35e7b552bdb109d8d2d5dbe766a961e38e1ad562875289544ae",
    },
    "bilibili": {
        "danmaku_ass.py": "3f3d7c51af875bb8ba0d093215a182712db513f4676a2ae5c688afc8bf595041",
        "group.json": "46873f8ee7a28c6c8ab2caf650eed9c3461d4d44135c1eb1616f7bcb1852a6ca",
        "locales/en.json": "3e008f89f56ee584c4a2edb25e689f60c8e51930cfbedc2c2a18ccaa49fd9806",
        "locales/ja.json": "79a4a5b1c4c3c7a01c56e0ca3815e2e5a2934e9463a3b32455746c1a824a2af5",
        "locales/zh-CN.json": "7c61cf1f204b6300577c3bc8ce5aba37aceff6fc0417db555ea7818147966e4b",
        "locales/zh-TW.json": "afdb7b54974f8bf02e5316c65b3927f23bdfd09fd6257dcbcaae343bda4a2707",
        "provider.py": "158d3a5fdc49dad7650e14dc206b979465a96b51f95f9dc55e6d5b0fd9a031dc",
        "provider.json": "ebf0c166ce2e43479ab1f8f824b192ac9d36c40d519213b2cf336a1102a0800b",
        "site-matrix.json": "409b77fe1ee921eab417064399ea57e7bc2555a63ea6f9fa9603459b5c3fb802",
    },
    "bilibili-search": {
        "provider.py": "f6af795067fca4306ec0030c7031b2e191eada3745851b7e41559b849da27115",
        "provider.json": "767a4be4d858c5843c44b52c20c1781ccb0f3e5e5b5ff9654a1565bff987ff34",
    },
    "generic-ytdlp": {
        "provider.py": "b7a87e87a88cd2fd35122d9f3a71381c9b77a1f1260cf62e6caaf6d0ef8b735b",
        "provider.json": "23078fd4c45fd250306917973e5f20ba7c15ee423274e7342efae15afc304179",
        "site-matrix.json": "323947cfa84d5b5b21321dc804e73755abadeb3da9f22ffd120416615e954ce5",
    },
    "youtube-player": {
        "provider.py": "972c899b078849b2497929d479bdeefda0b878a9f0d7d1320f0460b6942efaaa",
        "provider.json": "1066e7d0f6ffbb1522049541013cbc8456a9b7a641ce82e862fdfa276c569ca7",
    },
    "youtube-auto-split": {
        "provider.py": "654c6b416376c5c010f72c6c22e993cb408b61b74020e1e3f8bdb20fb37a66f1",
        "provider.json": "e0244a55fe13a9fa7feee5caad1f4756556c1eb9fc891699a8101ba87a8d1bde",
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
        "provider.json": "c65f123a2bfd01a3e3b97d823abd8552ee53a9e24d9ec0ddaa0764dc44fa6819",
    },
    "youtube": {
        "group.json": "73e2bd4a2806f7bc5875bd73ba5de850783d3c1ce143e5bc95add5f39283839e",
        "locales/en.json": "07ae9a731b2eedc93c925082091df97fa55d25e6ea7310504607fa7d2ac66a2a",
        "locales/ja.json": "02536cf0599ff5e866044db79812f8a147ee4775d6b019980246cf6bcd55f7ce",
        "locales/zh-CN.json": "aecb2c1652049bbc57280f4a70ab8e8912d635a7f7516b57c4a46ce7ed43472a",
        "locales/zh-TW.json": "6ab7e060426c53add0a1f9f552ff261572eb2c089d5d3d671c334958198e75b0",
        "provider.py": "cf5756e5204d85f329adab2ebb8ffeca72b111b7bb299982ec79c810e626ccd7",
        "provider.json": "872ebaf9658b712c45ba11dffdd439997674361852646ffedbf383cb0d69c3a7",
        "site-matrix.json": "4654a003d2d835585c3a5ca8871e132830b335a4faf1a914cbb6df63e248d1fa",
    }
}

