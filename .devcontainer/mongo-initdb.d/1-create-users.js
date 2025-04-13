var adminDb = db.getSiblingDB('admin');

adminDb.createUser({
    user: "app_user",
    pwd: "app_user",
    roles: [
        {
            role: "readWrite",
            db: "chats"
        },
        {
            role: "readWrite",
            db: "api"
        },
        {
            role: "readWrite",
            db: "vectorizer"
        }
    ]
});

adminDb.grantRolesToUser(
    "app_user",
    [
        {
            role: "clusterMonitor",
            db: "admin"
        }
    ]
)
