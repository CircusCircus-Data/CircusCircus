# CircusCircus Lab — UML Diagram (After)

This document describes the final Sound Lab architecture after the forum,
account-management, messaging, media, reaction, profile, music collection, and
Docker features were added.

## 1. Deployment and System Architecture

```mermaid
flowchart LR
    Browser["Browser"]

    subgraph Docker["Docker Compose private network"]
        subgraph Web["web container"]
            Gunicorn["Gunicorn<br/>0.0.0.0:5000"]
            Flask["Flask application"]
            Templates["Jinja templates<br/>CSS and images"]
            ORM["Flask-SQLAlchemy"]
        end

        subgraph Database["db container"]
            MySQL[("MySQL 8.4<br/>db:3306")]
        end
    end

    Volume[("mysql_data<br/>named volume")]
    MusicBrainz["MusicBrainz API"]
    CoverArt["Cover Art Archive"]

    Browser -->|"localhost:5001"| Gunicorn
    Gunicorn --> Flask
    Flask --> Templates
    Flask --> ORM
    ORM -->|"PyMySQL"| MySQL
    MySQL --> Volume
    Flask -->|"release search"| MusicBrainz
    Templates -->|"cover images"| CoverArt
```

## 2. Application Components

```mermaid
flowchart TB
    Factory["Application factory<br/>create_app()"]
    Config["Config<br/>environment and database URL"]
    Auth["auth blueprint<br/>registration, login, logout"]
    Posts["posts blueprint<br/>browse, create, view, edit, delete"]
    Comments["comments blueprint<br/>create, edit, delete"]
    Reactions["reactions blueprint<br/>like, dislike, heart"]
    Messages["messages blueprint<br/>inbox, conversation, send"]
    Settings["settings blueprint<br/>identity, password, delete account"]
    Profiles["profiles blueprint<br/>profiles, avatars, collections"]
    Formatting["formatting service<br/>Markdown and HTML sanitization"]
    Media["media service<br/>image and video validation"]
    MBClient["MusicBrainz client<br/>rate-conscious release search"]
    Models["SQLAlchemy models"]
    UI["Jinja presentation layer"]

    Factory --> Config
    Factory --> Auth
    Factory --> Posts
    Factory --> Comments
    Factory --> Reactions
    Factory --> Messages
    Factory --> Settings
    Factory --> Profiles

    Auth --> Models
    Posts --> Models
    Comments --> Models
    Reactions --> Models
    Messages --> Models
    Settings --> Models
    Profiles --> Models

    Posts --> Formatting
    Posts --> Media
    Profiles --> MBClient

    Auth --> UI
    Posts --> UI
    Comments --> UI
    Reactions --> UI
    Messages --> UI
    Settings --> UI
    Profiles --> UI
```

## 3. Domain Class Diagram

```mermaid
classDiagram
    direction LR

    class User {
        +Integer id PK
        +String username UK
        +String password_hash
        +String email UK
        +Boolean admin
        +check_password(password) Boolean
        +set_password(password)
    }

    class Profile {
        +Integer id PK
        +Integer user_id FK UK
        +String display_name
        +Text bio
        +String location
        +String instruments
        +String favorite_genres
        +String avatar_style
    }

    class CollectionItem {
        +Integer id PK
        +Integer user_id FK
        +String musicbrainz_id
        +String artist_name
        +String release_title
        +String release_date
        +String release_format
        +String cover_url
        +String personal_note
        +Boolean favorite
        +DateTime added_at
    }

    class Subforum {
        +Integer id PK
        +String title UK
        +Text description
        +Integer parent_id FK
        +Boolean hidden
    }

    class Post {
        +Integer id PK
        +String title
        +Text content
        +String image_url
        +String video_url
        +String visibility
        +Integer user_id FK
        +Integer subforum_id FK
        +DateTime postdate
        +get_time_string() String
    }

    class Comment {
        +Integer id PK
        +Text content
        +DateTime postdate
        +Integer user_id FK
        +Integer post_id FK
        +get_time_string() String
    }

    class Reaction {
        +Integer id PK
        +String reaction_type
        +Integer user_id FK
        +Integer post_id FK
    }

    class Message {
        +Integer id PK
        +Text content
        +DateTime sent_at
        +Boolean is_read
        +Integer sender_id FK
        +Integer recipient_id FK
    }

    User "1" *-- "0..1" Profile : profile
    User "1" *-- "0..*" CollectionItem : collection
    User "1" *-- "0..*" Post : authors
    User "1" *-- "0..*" Comment : writes
    User "1" *-- "0..*" Reaction : makes
    User "1" --> "0..*" Message : sends
    User "1" --> "0..*" Message : receives

    Subforum "0..1" --> "0..*" Subforum : parent and children
    Subforum "1" --> "0..*" Post : contains
    Post "1" *-- "0..*" Comment : contains
    Post "1" *-- "0..*" Reaction : receives
```

## 4. Main User Flows

```mermaid
flowchart TD
    Visitor["Visitor"] --> Browse["Browse public subforums and posts"]
    Visitor --> Register["Register or log in"]
    Register --> Member["Authenticated member"]

    Member --> ManagePosts["Create, edit, or delete own posts"]
    Member --> ManageComments["Create, edit, or delete own comments"]
    Member --> React["Like, dislike, or heart a post"]
    Member --> Messaging["Send and read private messages"]
    Member --> Account["Update account or change password"]
    Member --> Profile["Edit public music profile and avatar"]
    Member --> Search["Search MusicBrainz releases"]
    Search --> Collection["Add or remove collection items"]

    Admin["Administrator"] --> Moderate["Edit or delete posts and comments"]
    Moderate --> ManagePosts
    Moderate --> ManageComments

    Account --> DeleteDecision{"Message history exists?"}
    DeleteDecision -->|"Yes"| BlockDelete["Block account deletion<br/>to preserve messages"]
    DeleteDecision -->|"No"| DeleteAccount["Delete account and owned forum data"]
```

## 5. Relationship and Integrity Rules

| Source | Cardinality | Target | Rule |
| --- | ---: | --- | --- |
| User | 1 → 0..1 | Profile | Each user has at most one public profile. |
| User | 1 → many | CollectionItem | A user owns a music collection. |
| User | 1 → many | Post | Deleting an eligible account deletes its posts. |
| User | 1 → many | Comment | Users author comments on posts. |
| User | 1 → many | Reaction | One reaction is allowed per user and post. |
| User | 1 → many | Message | A message has one sender and one recipient. |
| Subforum | 1 → many | Post | Each post belongs to one subforum. |
| Subforum | 0..1 → many | Subforum | Subforums form a parent/child hierarchy. |
| Post | 1 → many | Comment | Deleting a post cascades to its comments. |
| Post | 1 → many | Reaction | Deleting a post cascades to its reactions. |

Additional constraints:

- `Post.visibility` is limited to `public` or `private`.
- `Reaction.reaction_type` is limited to `like`, `dislike`, or `heart`.
- `(Reaction.user_id, Reaction.post_id)` is unique.
- `(CollectionItem.user_id, CollectionItem.musicbrainz_id)` is unique.
- `Profile.user_id` is unique.
- Media is represented by optional URLs on `Post`; it is not a separate entity.
- Passwords are stored as hashes, never as plaintext.
- Account deletion is blocked when direct-message history exists.

## Legend

| Symbol | Meaning |
| --- | --- |
| PK | Primary key |
| FK | Foreign key |
| UK | Unique key |
| `*--` | Composition / cascade-owned relationship |
| `-->` | Association |

