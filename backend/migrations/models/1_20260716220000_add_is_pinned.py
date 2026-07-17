from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "projects" ADD COLUMN "is_pinned" BOOLEAN NOT NULL DEFAULT FALSE;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "projects" DROP COLUMN "is_pinned";
    """


MODELS_STATE = (
    "eJztlW1v2jAQx79KlFedtFVtBm21dyllKtOAqc0e1GmKTGKChWOntrMWdXz3+ZyEPAECqd"
    "WKtHfO/+7su1/suyc75iGm8tjFggQz+4P1ZDMUY71oWN5aNkqSUgdBoQk1rqj0mUglUKC0"
    "OkVUYi2FWAaCJIpwplWWUgoiD7QjYVEppYzcp9hXPMJqhoU2/PylZcJC/Ihl8ZnM/SnBNK"
    "ylSkI42+i+WiRGGzD10TjCaRM/4DSNWemcLNSMs5U3YQrUCDMskMKwvRIppA/Z5XUWFWWZ"
    "li5ZipWYEE9RSlWl3B0ZBJwBP52NNAVGcMo757Rz3rl4f9a50C4mk5VyvszKK2vPAg2BkW"
    "cvjR0plHkYjCW331hISKkFrzdDYj29SkgDoU68ibAAto1hIZQQy4vzTBRj9OhTzCIFF9zp"
    "drcw++be9K7dmyPt9Qaq4foyZ3d8lJuczAZgS5DwNPaAmLsfJsDTk5MdAGqvjQCNrQ5Qn6"
    "hw9gbrED/djkfrIVZCGiBDEijrj0WJbD3q1wF0Cz+oF5KOpbynVWxHQ/dHk2jv8/jS1M+l"
    "ioTZxWxwqelCs5zOK88ehAkK5g9IhH7Lwh2+ybdtip24qSCGIsMKKob68vHxVZpW3horRt"
    "86VNLC4/9IOaCRAn/NrPdoh9WY5+mJL06x1hG7uzTE7uZ+2G21QxwjQvdBuAo4RH4vMpID"
    "gaFgH60ZKlfaokiMNwyWWmRztuShx8XidU4YW9cQjhld5P9uC19vMOzfeu7wS23sXLleHy"
    "yOURcN9eis8StWm1jfB961BZ/W3XjUb06nlZ93Z0NOKFXcZ/zBR2HlmhVqAebfDrPlXxQ0"
    "L7I="
)
