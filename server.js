const express = require("express");
const cron = require("node-cron");
const axios = require("axios");
const multer = require("multer");
const fs = require("fs");
const path = require("path");
const cors = require("cors");

const app = express();
const PORT = process.env.PORT || 8080;

app.use(cors());
app.use(express.json());
app.use(express.static("public"));

// Storage for posts queue (in production use a database)
let postsQueue = [];
let publishedPosts = [];
let pages = [];

// Multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const dir = "uploads/";
    if (!fs.existsSync(dir)) fs.mkdirSync(dir);
    cb(null, dir);
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + path.extname(file.originalname));
  },
});
const upload = multer({ storage, limits: { fileSize: 100 * 1024 * 1024 } });

// ============================================================
//  FACEBOOK API FUNCTIONS
// ============================================================

// نشر بوست نص
async function publishTextPost(pageId, token, message) {
  const res = await axios.post(
    `https://graph.facebook.com/v19.0/${pageId}/feed`,
    { message, access_token: token }
  );
  return res.data;
}

// نشر بوست صورة
async function publishPhotoPost(pageId, token, message, imageUrl) {
  const res = await axios.post(
    `https://graph.facebook.com/v19.0/${pageId}/photos`,
    { caption: message, url: imageUrl, access_token: token }
  );
  return res.data;
}

// نشر بوست صورة من ملف
async function publishPhotoFromFile(pageId, token, message, filePath) {
  const FormData = require("form-data");
  const form = new FormData();
  form.append("caption", message);
  form.append("source", fs.createReadStream(filePath));
  form.append("access_token", token);
  const res = await axios.post(
    `https://graph.facebook.com/v19.0/${pageId}/photos`,
    form,
    { headers: form.getHeaders() }
  );
  return res.data;
}

// نشر فيديو
async function publishVideo(pageId, token, title, description, videoUrl) {
  const res = await axios.post(
    `https://graph.facebook.com/v19.0/${pageId}/videos`,
    { title, description, file_url: videoUrl, access_token: token }
  );
  return res.data;
}

// نشر رابط
async function publishLinkPost(pageId, token, message, link) {
  const res = await axios.post(
    `https://graph.facebook.com/v19.0/${pageId}/feed`,
    { message, link, access_token: token }
  );
  return res.data;
}

// الدالة الرئيسية للنشر
async function publishPost(post) {
  const results = [];
  for (const page of post.pages) {
    try {
      let result;
      switch (post.type) {
        case "text":
          result = await publishTextPost(page.pageId, page.token, post.message);
          break;
        case "image":
          if (post.filePath) {
            result = await publishPhotoFromFile(page.pageId, page.token, post.message, post.filePath);
          } else {
            result = await publishPhotoPost(page.pageId, page.token, post.message, post.mediaUrl);
          }
          break;
        case "video":
          result = await publishVideo(page.pageId, page.token, post.title || "فيديو", post.message, post.mediaUrl);
          break;
        case "link":
          result = await publishLinkPost(page.pageId, page.token, post.message, post.link);
          break;
      }
      results.push({ pageId: page.pageId, pageName: page.name, success: true, postId: result.id });
      console.log(`✅ نُشر على ${page.name}: ${result.id}`);
    } catch (err) {
      const errMsg = err.response?.data?.error?.message || err.message;
      results.push({ pageId: page.pageId, pageName: page.name, success: false, error: errMsg });
      console.error(`❌ فشل النشر على ${page.name}: ${errMsg}`);
    }
  }
  return results;
}

// ============================================================
//  SCHEDULER - يشتغل كل دقيقة ويتحقق من البوستات
// ============================================================
cron.schedule("* * * * *", async () => {
  const now = new Date();
  const currentTime = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  const today = now.toISOString().split("T")[0];

  const duePosts = postsQueue.filter(
    (p) => p.status === "pending" && p.scheduleTime === currentTime && p.scheduleDate === today
  );

  for (const post of duePosts) {
    console.log(`⏰ حان وقت نشر: ${post.message.slice(0, 40)}...`);
    post.status = "publishing";
    const results = await publishPost(post);
    const allSuccess = results.every((r) => r.success);
    post.status = allSuccess ? "published" : results.some((r) => r.success) ? "partial" : "failed";
    post.publishedAt = new Date().toISOString();
    post.results = results;

    // Handle repeat
    if (post.repeat !== "once") {
      const nextPost = { ...post, id: Date.now(), status: "pending", results: [] };
      if (post.repeat === "daily") {
        const next = new Date(now);
        next.setDate(next.getDate() + 1);
        nextPost.scheduleDate = next.toISOString().split("T")[0];
      } else if (post.repeat === "weekly") {
        const next = new Date(now);
        next.setDate(next.getDate() + 7);
        nextPost.scheduleDate = next.toISOString().split("T")[0];
      }
      postsQueue.push(nextPost);
    }

    publishedPosts.unshift(post);
    postsQueue = postsQueue.filter((p) => p.id !== post.id);
  }
});

// ============================================================
//  API ROUTES
// ============================================================

// الصفحات
app.get("/api/pages", (req, res) => res.json(pages));

app.post("/api/pages", (req, res) => {
  const { name, pageId, token } = req.body;
  if (!name || !pageId || !token) return res.status(400).json({ error: "بيانات ناقصة" });
  const page = { id: Date.now().toString(), name, pageId, token, active: true, addedAt: new Date().toISOString() };
  pages.push(page);
  res.json({ success: true, page });
});

app.patch("/api/pages/:id", (req, res) => {
  const page = pages.find((p) => p.id === req.params.id);
  if (!page) return res.status(404).json({ error: "الصفحة مش موجودة" });
  Object.assign(page, req.body);
  res.json({ success: true, page });
});

app.delete("/api/pages/:id", (req, res) => {
  pages = pages.filter((p) => p.id !== req.params.id);
  res.json({ success: true });
});

// التحقق من Token
app.post("/api/pages/verify", async (req, res) => {
  const { pageId, token } = req.body;
  try {
    const result = await axios.get(
      `https://graph.facebook.com/v19.0/${pageId}?fields=name,fan_count&access_token=${token}`
    );
    res.json({ success: true, page: result.data });
  } catch (err) {
    res.json({ success: false, error: err.response?.data?.error?.message || "Token خاطئ" });
  }
});

// قائمة النشر
app.get("/api/queue", (req, res) => res.json({ pending: postsQueue, published: publishedPosts.slice(0, 50) }));

app.post("/api/queue", upload.single("file"), (req, res) => {
  const { type, message, mediaUrl, link, scheduleTime, scheduleDate, repeat, pageIds } = req.body;
  const selectedPageIds = JSON.parse(pageIds || "[]");
  const selectedPages = pages.filter((p) => selectedPageIds.includes(p.id) && p.active);

  if (!message) return res.status(400).json({ error: "النص مطلوب" });
  if (selectedPages.length === 0) return res.status(400).json({ error: "اختار صفحة واحدة على الأقل" });

  const post = {
    id: Date.now(),
    type: type || "text",
    message,
    mediaUrl: mediaUrl || null,
    filePath: req.file ? req.file.path : null,
    link: link || null,
    pages: selectedPages,
    scheduleTime: scheduleTime || "10:00",
    scheduleDate: scheduleDate || new Date().toISOString().split("T")[0],
    repeat: repeat || "once",
    status: "pending",
    createdAt: new Date().toISOString(),
    results: [],
  };

  postsQueue.push(post);
  console.log(`📝 بوست جديد أُضيف: ${message.slice(0, 40)}... موعده ${scheduleTime}`);
  res.json({ success: true, post });
});

app.post("/api/queue/:id/publish-now", async (req, res) => {
  const post = postsQueue.find((p) => p.id == req.params.id);
  if (!post) return res.status(404).json({ error: "البوست مش موجود" });
  post.status = "publishing";
  const results = await publishPost(post);
  post.status = results.every((r) => r.success) ? "published" : "failed";
  post.results = results;
  post.publishedAt = new Date().toISOString();
  publishedPosts.unshift(post);
  postsQueue = postsQueue.filter((p) => p.id != req.params.id);
  res.json({ success: true, results });
});

app.delete("/api/queue/:id", (req, res) => {
  postsQueue = postsQueue.filter((p) => p.id != req.params.id);
  res.json({ success: true });
});

// إحصائيات
app.get("/api/stats", (req, res) => {
  const today = new Date().toISOString().split("T")[0];
  res.json({
    totalPages: pages.length,
    activePages: pages.filter((p) => p.active).length,
    pendingPosts: postsQueue.length,
    publishedToday: publishedPosts.filter((p) => p.publishedAt?.startsWith(today)).length,
    totalPublished: publishedPosts.length,
  });
});

// Health check
app.get("/health", (req, res) => res.json({ status: "ok", time: new Date().toISOString() }));

app.listen(PORT, () => {
  console.log(`🚀 AutoPost Server شغال على البورت ${PORT}`);
  console.log(`📅 Scheduler نشط ويفحص كل دقيقة`);
});
