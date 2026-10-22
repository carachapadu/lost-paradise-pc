/* System functions only Fist of the North Star: Lost Paradise (CUSA12781 1.09) imports. All describe
 * an offline console: no live streaming, no recording, no Remote Play, no network. The calls that
 * only switch such features on or off succeed without doing anything. */
#include <stdint.h>
#include <string.h>
#include "runtime.h"

static ABI int32_t ok(void) { return 0; }
/* ---- sceZlib: the PS4's hardware inflate, done on the CPU when the request is made. ----
 * Self-contained (the probe links no zlib): a zlib stream (2-byte header, deflate, Adler-32) is
 * inflated into the caller's buffer; the request finishes at once, so WaitForDone returns at once.
 * Contracts (OpenOrbis zlib.h, to confirm against the game's call sites in Ghidra):
 *   sceZlibInitialize(buffer, size); sceZlibInflate(src, srcLen, dst, dstLen, *requestId);
 *   sceZlibWaitForDone(*requestId, *timeout); sceZlibGetResult(requestId, *length, *status). */
typedef struct { const uint8_t *in; uint32_t inlen, inpos; uint8_t *out; uint32_t outlen, outpos; uint32_t bitbuf; int bitcnt; int err; } Inf;
typedef struct { uint16_t count[16], symbol[288]; } Huff;
static int bits(Inf *s, int need) {
    uint32_t v = s->bitbuf;
    while (s->bitcnt < need) {
        if (s->inpos >= s->inlen) { s->err = 1; return 0; }
        v |= (uint32_t)s->in[s->inpos++] << s->bitcnt; s->bitcnt += 8;
    }
    s->bitbuf = v >> need; s->bitcnt -= need;
    return (int)(v & ((1u << need) - 1));
}
static int decode(Inf *s, const Huff *h) {
    int code = 0, first = 0, index = 0;
    for (int len = 1; len <= 15; ++len) {
        code |= bits(s, 1); if (s->err) return -1;
        int count = h->count[len];
        if (code - count < first) return h->symbol[index + (code - first)];
        index += count; first += count; first <<= 1; code <<= 1;
    }
    return -1;
}
static int construct(Huff *h, const uint16_t *length, int n) {
    uint16_t offs[16]; memset(h->count, 0, sizeof h->count);
    for (int i = 0; i < n; ++i) h->count[length[i]]++;
    if (h->count[0] == n) return 0;
    int left = 1;
    for (int len = 1; len <= 15; ++len) { left <<= 1; left -= h->count[len]; if (left < 0) return left; }
    offs[1] = 0;
    for (int len = 1; len < 15; ++len) offs[len + 1] = offs[len] + h->count[len];
    for (int i = 0; i < n; ++i) if (length[i]) h->symbol[offs[length[i]]++] = (uint16_t)i;
    return left;
}
static int codes(Inf *s, const Huff *lc, const Huff *dc) {
    static const uint16_t lens[29] = {3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258};
    static const uint16_t lext[29] = {0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0};
    static const uint16_t dists[30] = {1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577};
    static const uint16_t dext[30] = {0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13};
    for (;;) {
        int sym = decode(s, lc); if (sym < 0) return -1;
        if (sym < 256) { if (s->outpos >= s->outlen) return -2; s->out[s->outpos++] = (uint8_t)sym; }
        else if (sym == 256) return 0;
        else {
            sym -= 257; if (sym >= 29) return -1;
            uint32_t len = lens[sym] + (uint32_t)bits(s, lext[sym]);
            int ds = decode(s, dc); if (ds < 0 || ds >= 30) return -1;
            uint32_t dist = dists[ds] + (uint32_t)bits(s, dext[ds]);
            if (s->err || dist > s->outpos) return -1;
            if (s->outpos + len > s->outlen) return -2;
            while (len--) { s->out[s->outpos] = s->out[s->outpos - dist]; ++s->outpos; }
        }
    }
}
static int inflate_block_loop(Inf *s) {
    int last;
    do {
        last = bits(s, 1); int type = bits(s, 2); if (s->err) return -1;
        if (type == 0) {
            s->bitbuf = 0; s->bitcnt = 0;
            if (s->inpos + 4 > s->inlen) return -1;
            uint32_t len = s->in[s->inpos] | (uint32_t)s->in[s->inpos + 1] << 8;
            if ((len ^ 0xffff) != (s->in[s->inpos + 2] | (uint32_t)s->in[s->inpos + 3] << 8)) return -1;
            s->inpos += 4;
            if (s->inpos + len > s->inlen) return -1;
            if (s->outpos + len > s->outlen) return -2;
            memcpy(s->out + s->outpos, s->in + s->inpos, len); s->inpos += len; s->outpos += len;
        } else if (type == 1) {
            Huff lc, dc; uint16_t l[288];
            for (int i = 0; i < 144; ++i) l[i] = 8;
            for (int i = 144; i < 256; ++i) l[i] = 9;
            for (int i = 256; i < 280; ++i) l[i] = 7;
            for (int i = 280; i < 288; ++i) l[i] = 8;
            construct(&lc, l, 288);
            for (int i = 0; i < 30; ++i) l[i] = 5;
            construct(&dc, l, 30);
            int r = codes(s, &lc, &dc); if (r) return r;
        } else if (type == 2) {
            static const uint8_t order[19] = {16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15};
            uint16_t l[320]; Huff lc, dc;
            int nlen = bits(s, 5) + 257, ndist = bits(s, 5) + 1, ncode = bits(s, 4) + 4;
            if (s->err || nlen > 286 || ndist > 30) return -1;
            int i;
            for (i = 0; i < ncode; ++i) l[order[i]] = (uint16_t)bits(s, 3);
            for (; i < 19; ++i) l[order[i]] = 0;
            if (construct(&lc, l, 19) != 0) return -1;
            for (i = 0; i < nlen + ndist;) {
                int sym = decode(s, &lc); if (sym < 0) return -1;
                if (sym < 16) l[i++] = (uint16_t)sym;
                else {
                    int len = 0, rep;
                    if (sym == 16) { if (!i) return -1; len = l[i - 1]; rep = 3 + bits(s, 2); }
                    else if (sym == 17) rep = 3 + bits(s, 3); else rep = 11 + bits(s, 7);
                    if (i + rep > nlen + ndist) return -1;
                    while (rep--) l[i++] = (uint16_t)len;
                }
            }
            if (l[256] == 0) return -1;
            int e = construct(&lc, l, nlen); if (e < 0 || (e > 0 && nlen - lc.count[0] != 1)) return -1;
            e = construct(&dc, l + nlen, ndist); if (e < 0 || (e > 0 && ndist - dc.count[0] != 1)) return -1;
            int r = codes(s, &lc, &dc); if (r) return r;
        } else return -1;
    } while (!last);
    return 0;
}
/* Returns the inflated size, or -1 (bad data) / -2 (output buffer too small). */
int64_t hokuto_zlib_inflate(const uint8_t *src, uint32_t srclen, uint8_t *dst, uint32_t dstlen) {
    const int zheader = srclen >= 2 && (src[0] & 0x0f) == 8 && !(((src[0] << 8) | src[1]) % 31) && !(src[1] & 0x20);
    Inf s = { src, srclen, zheader ? 2u : 0u, dst, dstlen, 0, 0, 0, 0 }; /* no header: raw deflate */
    int r = inflate_block_loop(&s);
    return r ? r : (int64_t)s.outpos;
}
#define ZLIB_REQUESTS 64
static struct { uint64_t id; int64_t length; int32_t status; } zreq[ZLIB_REQUESTS];
static uint64_t znext = 1;
static ABI int32_t zlib_init(const void *buffer, uint64_t size) { (void)buffer; (void)size; return 0; }
static ABI int32_t zlib_inflate(const uint8_t *src, uint32_t srclen, uint8_t *dst, uint32_t dstlen, uint64_t *id) {
    if (!src || !dst || !id) return (int32_t)0x80000001;
    int64_t n = hokuto_zlib_inflate(src, srclen, dst, dstlen);
    uint64_t rid = znext++;
    unsigned slot = (unsigned)(rid % ZLIB_REQUESTS);
    zreq[slot].id = rid; zreq[slot].length = n < 0 ? 0 : n;
    zreq[slot].status = n >= 0 ? 0 : n == -2 ? (int32_t)0x80000003 : (int32_t)0x80000004;
    *id = rid;
    return 0;
}
static ABI int32_t zlib_wait(const uint64_t *id, const uint32_t *timeout) { (void)id; (void)timeout; return 0; }
static ABI int32_t zlib_result(uint64_t id, uint32_t *length, int32_t *status) {
    unsigned slot = (unsigned)(id % ZLIB_REQUESTS);
    if (zreq[slot].id != id) return (int32_t)0x80000001;
    if (length) *length = (uint32_t)zreq[slot].length;
    if (status) *status = zreq[slot].status;
    return 0;
}

/* sceGameLiveStreamingGetCurrentStatus(status): not broadcasting. */
/* sceImeDialogGetPanelSize(param, width, height): a keyboard panel is never shown (text entry goes
 * through the game window), so only a plausible size is reported for the game's layout. */
static ABI int32_t ime_panel_size(const void *param, uint32_t *width, uint32_t *height) {
    (void)param; if (width) *width = 1280; if (height) *height = 360; return 0;
}
/* sceKernelGetCpumode(): 0, the base console (the game then skips its sceKernelSetFsstParam call). */
static ABI int32_t cpumode(void) { return 0; }
static ABI int32_t live_status(void *status) { if (status) memset(status, 0, 4); return 0; }
/* sceUserServiceGetUserColor(userId, color): the first player's colour (blue). */
static ABI int32_t user_color(int32_t user, int32_t *color) { (void)user; if (color) *color = 0; return 0; }

static const RuntimeExport exports[] = {
    {"sceGameLiveStreamingInitialize", ok}, {"sceGameLiveStreamingTerminate", ok},
    {"sceGameLiveStreamingEnableLiveStreaming", ok}, {"sceGameLiveStreamingPermitLiveStreaming", ok},
    {"sceGameLiveStreamingPermitServerSideRecording", ok}, {"sceGameLiveStreamingGetCurrentStatus", live_status},
    {"sceGameLiveStreamingGetProgramInfo", ok}, {"sceGameLiveStreamingSetCameraFrameSetting", ok},
    {"sceGameLiveStreamingSetInvitationSessionId", ok}, {"sceGameLiveStreamingSetMaxBitrate", ok},
    {"sceGameLiveStreamingSetMetadata", ok},
    {"sceScreenShotEnable", ok}, {"sceScreenShotDisable", ok}, {"sceScreenShotSetOverlayImage", ok},
    {"sceSharePlayInitialize", ok}, {"sceSharePlayTerminate", ok}, {"sceSharePlaySetProhibition", ok},
    {"sceVideoRecordingSetInfo", ok},
    {"sceRemoteplayInitialize", ok}, {"sceRemoteplayTerminate", ok},
    {"sceRudpInit", ok}, {"sceRudpEnd", ok}, {"sceRudpEnableInternalIOThread", ok},
    {"sceUserServiceGetUserColor", user_color},
    {"sceZlibInitialize", zlib_init}, {"sceZlibFinalize", ok}, {"sceZlibInflate", zlib_inflate},
    {"sceZlibWaitForDone", zlib_wait}, {"sceZlibGetResult", zlib_result},
    {"sceKernelGetCpumode", cpumode}, {"sceImeDialogGetPanelSize", ime_panel_size}, {"sceKernelSetFsstParam", ok},
    {"sceVideoOutCursorEnable", ok}, {"sceVideoOutCursorDisable", ok}, {"sceVideoOutCursorSetPosition", ok},
    {"sceVideoOutCursorSetHotSpot", ok}, {"sceVideoOutCursorSetImageAddress", ok},
};
uintptr_t runtime_hokuto_resolve(const char *name) { return RUNTIME_LOOKUP(exports, name); }
