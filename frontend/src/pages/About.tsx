import { Link } from 'react-router-dom'
import { BulldogMark } from '../components/BulldogMark'

export function About() {
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">About us</p>
        <h1>Yale blue, kept honest.</h1>
        <p className="page-lede">
          Campus Customs sells officially licensed Yale apparel from Broadway in New
          Haven. We are a shop first — the kind where someone will tell you a crewneck
          runs roomy, or that the size you want went out last week and is worth waiting
          for.
        </p>
      </section>

      <section className="prose">
        <h2>What we carry</h2>
        <p>
          Crewnecks, hoodies, quarter-zips, tees, and a handful of jackets — the pieces
          that get worn to class, to the gym, to the game, and home for winter break. Our
          catalogue runs from a straightforward tee to a heavyweight fleece, and every
          style comes in six sizes, XS through XXL.
        </p>
        <p>
          Everything bears officially licensed Yale marks. That matters more than it
          sounds: it means the shield is the right shield, the blue is the right blue,
          and the university sees a share of what you spend.
        </p>

        <h2>How we talk about stock</h2>
        <p>
          A lot of shops quietly show you things they cannot send. We would rather not.
          The size and quantity you see on a product page is read live from our inventory
          at the moment the page loads — so when a size is listed, it is on the shelf, and
          when it isn't listed, we say so plainly instead of taking the order and
          apologising later.
        </p>
        <p>
          The same applies to colour. If a jersey is navy and white, we will tell you it
          is navy and white, even when you were hoping for pink. A short honest answer is
          worth more than a sale we have to undo.
        </p>

        <h2>Service, in practice</h2>
        <p>
          Ask us anything about what we carry and you will get a straight answer: what a
          piece looks like, what it costs, which sizes are available right now. If the
          answer is something we genuinely do not know — how a fabric washes after a year,
          when a sold-out size comes back — we will say that rather than invent it.
        </p>
        <p>
          Our assistant in the corner of this page works the same way. It reads from the
          same catalogue and the same stock counts we do, so it cannot tell you about
          something that is not really there.
        </p>

        <h2>Where to find us</h2>
        <p>
          57 Broadway, New Haven, Connecticut — in the middle of campus, a short walk from
          most of it. If you are nearby, come try things on. If you are not, the catalogue
          here is the same stock.
        </p>
      </section>

      <section className="band">
        <BulldogMark size={64} />
        <h2>Come say hello</h2>
        <p>
          Whether you have worn Yale blue for forty years or you are buying your first
          piece this week, you are the person this shop is for.
        </p>
        <Link to="/products" className="btn btn-light">
          Browse the catalogue
        </Link>
      </section>
    </>
  )
}
