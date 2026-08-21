# CircusCircus Lab — UML Diagram (Before)

## 1. High-Level Architecture (Layers)

```mermaid
flowchart LR
    subgraph Presentation["Presentation Layer<br/>Templates — HTML, CSS, JS"]
        T["base.html<br/>index.html<br/>forum.html<br/>subforum.html<br/>create_post.html<br/>viewpost.html<br/>createaccount.html<br/>login.html<br/>myaccount.html"]
    end

    subgraph Application["Application / Controller Layer<br/>Flask routes — routes.py"]
        R["/ — index()<br/>/forum — forum()<br/>/subforum — subforum()<br/>/addpost — addpost()<br/>/action_post — action_post()<br/>/viewpost — viewpost()<br/>/action_comment — action_comment()<br/>/createaccount — createaccount()<br/>/action_createaccount — action_createaccount()<br/>/login — login()<br/>/action_login — action_login()<br/>/logout — logout()<br/>/myaccount — myaccount()"]
    end

    subgraph Data["Data / Model Layer<br/>SQLAlchemy + Database"]
        M["User<br/>Subforum<br/>Post<br/>Comment"]
        DB[("SQLite Database<br/>circus.db")]
        M --> DB
    end

    T --> R --> M
```

### Presentation layer templates

| Template |
| --- |
| `base.html` |
| `index.html` |
| `forum.html` |
| `subforum.html` |
| `create_post.html` |
| `viewpost.html` |
| `createaccount.html` |
| `login.html` |
| `myaccount.html` |

### Application routes

| Route | Controller function |
| --- | --- |
| `/` | `index()` |
| `/forum` | `forum()` |
| `/subforum` | `subforum()` |
| `/addpost` | `addpost()` |
| `/action_post` | `action_post()` |
| `/viewpost` | `viewpost()` |
| `/action_comment` | `action_comment()` |
| `/createaccount` | `createaccount()` |
| `/action_createaccount` | `action_createaccount()` |
| `/login` | `login()` |
| `/action_login` | `action_login()` |
| `/logout` | `logout()` |
| `/myaccount` | `myaccount()` |

## 2. Route Map (Flows)

```mermaid
flowchart TD
    Home["HOME<br/>/<br/>index()"] --> Forum["FORUM<br/>/forum<br/>forum()"]
    Forum --> Subforum["SUBFORUM<br/>/subforum?id=&lt;id&gt;<br/>subforum()"]

    Subforum --> AddPost["ADD POST FORM<br/>/addpost?sub=&lt;id&gt;<br/>addpost()"]
    AddPost --> SubmitPost["SUBMIT POST<br/>POST /action_post?sub=&lt;id&gt;<br/>action_post()"]
    SubmitPost --> AddPost
    SubmitPost --> ViewPost["VIEW POST<br/>/viewpost?post=&lt;id&gt;<br/>viewpost()"]
    ViewPost -.-> AddPost

    ViewPost --> SubmitComment["SUBMIT COMMENT<br/>POST /action_comment?post=&lt;id&gt;<br/>action_comment()"]
    SubmitComment --> ViewPost

    CreateAccount["CREATE ACCOUNT<br/>/createaccount<br/>createaccount()"] --> SubmitAccount["SUBMIT ACCOUNT<br/>POST /action_createaccount<br/>action_createaccount()"]

    Login["LOGIN<br/>/login<br/>login()"] --> SubmitLogin["SUBMIT LOGIN<br/>POST /action_login<br/>action_login()"]
    SubmitLogin --> Logout["LOGOUT<br/>/logout<br/>logout()"]
```

## 3. Class Diagram (Models)

```mermaid
classDiagram
    direction LR

    class User {
        -Integer id PK
        -String username Unique
        -String password
        -String email Unique
        -DateTime join_date
        +__init__(username, email, password, join_date)
        +get_id() String
    }

    class Post {
        -Integer id PK
        -String title
        -String content
        -DateTime postdate
        -Integer user_id FK
        -Integer subforum_id FK
        +__init__(title, content, postdate)
        +add_comment(comment)
    }

    class Subforum {
        -Integer id PK
        -String title
        -String description
        -String path
        -Integer parent_id FK Self
        +__init__(title, description, parent_id, path)
        +add_post(post)
    }

    class Comment {
        -Integer id PK
        -String content
        -DateTime postdate
        -Integer user_id FK
        -Integer post_id FK
        +__init__(content, postdate)
        +__repr__()
    }

    User "1" --> "*" Post : posts / author
    User "1" --> "*" Comment : comments / author
    Subforum "1" --> "*" Post : posts / subforum
    Post "1" --> "*" Comment : comments / on post
    Subforum "0..1" --> "*" Subforum : children / subforums
```

## 4. Key Relationships

| Source | Cardinality | Target | Meaning |
| --- | ---: | --- | --- |
| User | 1 → many | Post | A user creates many posts. |
| User | 1 → many | Comment | A user writes many comments. |
| Post | 1 → many | Comment | A post has many comments. |
| Subforum | 1 → many | Post | A subforum contains many posts. |
| Subforum | 1 → many | Subforum | Self-referencing hierarchy. |

## 5. Notes

- **PK** = Primary Key
- **FK** = Foreign Key
- All relationships are implemented using SQLAlchemy ORM.
- Authentication is handled using Flask-Login (`UserMixin`).
- Passwords are stored securely using `werkzeug.security`.
- Database used: SQLite (`circus.db`).

## Legend

| Diagram element | Meaning |
| --- | --- |
| Model / Entity | A data model persisted through SQLAlchemy. |
| Route — Read (`GET`) | A route that displays existing data. |
| Route — Create (`GET` form / `POST`) | A form or action that creates data. |
| Route — Account Management | Registration, login, or logout flow. |
