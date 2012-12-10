
#ifndef SG_INTERFACE_H
#define SG_INTERFACE_H

#include <iostream>
#include <cstddef>

#include <boost/bind.hpp>
#include <boost/function.hpp>
#include <boost/utility.hpp>
#include <boost/intrusive_ptr.hpp>
#include <boost/cstdint.hpp>

namespace sg
{
using namespace std;
   
class ReferenceCounted
{
   int     m_nCount;
      
   friend void intrusive_ptr_add_ref( ReferenceCounted * );
   friend void intrusive_ptr_release( ReferenceCounted * );
      
  protected:
   ReferenceCounted() : m_nCount(0) {}
      
   virtual ~ReferenceCounted() {}
      
   virtual void onZeroRefcount() = 0;
};
   
inline void intrusive_ptr_add_ref( ReferenceCounted * r) 
{ 
   ++r->m_nCount;
}
   
inline void intrusive_ptr_release( ReferenceCounted * r)
{        
   if( --r->m_nCount == 0 ) 
      r->onZeroRefcount();
}

   
class ByteString;
class DataType;
class Instance;
class Message;
class Object;
class UUID;
class World;
class WorldInterface;
   
typedef boost::intrusive_ptr<Instance>       PInstance;
typedef boost::intrusive_ptr<Message>        PMessage;
typedef boost::intrusive_ptr<Object>         PObject;
typedef boost::intrusive_ptr<World>          PWorld;
typedef boost::intrusive_ptr<WorldInterface> PWorldInterface;
   
using boost::uint8_t;
using boost::int32_t;
using boost::uint32_t;
using boost::int64_t;
using boost::uint64_t;
   

   
enum BasicType
{
   TBOOL,
   TINT32,
   TUINT32,
   TINT64,
   TUINT64,
   TFLOAT,
   TDOUBLE,
   TBYTE_STRING,
   TUUID,
   TINSTANCE,
   MAX_BASIC_TYPE
};


typedef boost::function< void (const PObject  &) > NewObjectCallback;
typedef boost::function< void (const PMessage &) > NewMessageCallback;
typedef boost::function< void () >                 AttributeUpdateCallback;


struct AttributeID
{
   int nDerivationLevel;
   int nAttributeNumber;
       
   AttributeID( int d, int n ) : nDerivationLevel(d), nAttributeNumber(n)
   {}
       
   bool operator==( const AttributeID & rhs )
   { 
      return nDerivationLevel == rhs.nDerivationLevel && nAttributeNumber == rhs.nAttributeNumber;
   }
       
   bool operator<(  const AttributeID & rhs )
   {
      return nDerivationLevel < rhs.nDerivationLevel || nAttributeNumber < rhs.nAttributeNumber;
   }
};


class World : public ReferenceCounted, boost::noncopyable
{
  protected:
   World() {}
  public:
      
   virtual const char * getName() const = 0;
      
   virtual void printTypes() = 0;
};


class WorldInterface : public ReferenceCounted, boost::noncopyable
{
  protected:
   WorldInterface() {}
   
  public:

   virtual PObject     createObject( int nTypeId ) = 0;
   virtual PMessage    createMessage( int nTypeId ) = 0;
      
   virtual void setNewObjectHandler ( int nTypeId, const NewObjectCallback  & cb) = 0;
   virtual void setNewMessageHandler( int nTypeId, const NewMessageCallback & cb) = 0;

   virtual void registerAttributeUpdateCallback( const PObject & obj,
                                                 const AttributeID & attrId,
                                                 const AttributeUpdateCallback & cb ) = 0;

   virtual void runCallbacks() = 0;

      
   template <class T> T createObject()  { return T(createObject ( T::ID )); }
   template <class T> T createMessage() { return T(createMessage( T::ID )); }

   template<class T> static void new_obj_wrapper( const boost::function< void (const T &) > & cb,
                                                  const PObject & o )
   {
      cb( T(o) );
   }


   template <class T> void setNewObjectHandler( const boost::function< void (const T &) > & cb )
   {
      setNewObjectHandler( T::ID, boost::bind(new_obj_wrapper<T>, cb, _1) );
   }
};
   
   
   
class Object : public ReferenceCounted, boost::noncopyable
{
  protected:
   Object() {}
      
  public:
   
   virtual const UUID *    getUUID()            const = 0;
   virtual PInstance       getInstance()        const = 0;
   virtual PWorldInterface getOwningInterface() const = 0;

   virtual int getTypeId() const = 0;

   // The returned integer is 0 when this object is not of type
   // nTypeId or a subclass of nTypeId.
   // Otherwise, it returns a number indicating how deeply derived
   // this instance is from the specified type.
   //
   // For Class hierarchy A<--B<--C and assuming that A = typeId 1
   //
   //    An A object would return 1
   //    A  B object would return 2
   //    A  C object would return 3
   //
   // The purpose for this method is to allow the "closest type match"
   // to be used when registering callbacks for basetypes. Thus when
   // registering callback functions for types A, B, & C the most-specific
   // callback for the given object will be the one for which "isType()"
   // returns the smallest non-zero integer.
   //
   virtual int isType( int nTypeId ) const = 0;
};
   
   
   
class Message : public ReferenceCounted, boost::noncopyable
{
  protected:
   Message() {}
  public:
   virtual const UUID * getUUID()     const = 0;
   virtual PInstance    getInstance() const = 0;
};
   

   
class UUID 
{
  protected:
   UUID() {}
  public:
   virtual bool operator< ( const UUID * ) const = 0;
   virtual bool operator==( const UUID * ) const = 0;
};
   
   
   
class ByteString 
{
  protected:
   ByteString() {}
  public:
   virtual const uint8_t * data()   const = 0;
   virtual std::size_t     length() const = 0;
      
   virtual bool operator< ( const ByteString * ) const = 0;
   virtual bool operator==( const ByteString * ) const = 0;
   virtual bool operator==( const char *       ) const = 0;
};
   
         
   
   
//---------------------------------------------------------------------------------
// Update Callbacks
//
typedef boost::function< void () > UpdateCallback;
   
   
class Instance : public ReferenceCounted, boost::noncopyable
{
  protected:
   Instance() {}
      
  public:
      
      
   virtual BasicType getAttributeType( const AttributeID & attrId ) const = 0;
                  

   //---------------------------------------------------------------------------------
   // Data get/set
   //
   virtual bool               getBoolean    ( const AttributeID & attrId ) const = 0;
   virtual int32_t            getInt32      ( const AttributeID & attrId ) const = 0;
   virtual uint32_t           getUInt32     ( const AttributeID & attrId ) const = 0;
      
   virtual int64_t            getInt64      ( const AttributeID & attrId ) const = 0;
   virtual uint64_t           getUInt64     ( const AttributeID & attrId ) const = 0;
       
   virtual float              getFloat      ( const AttributeID & attrId ) const = 0;
   virtual double             getDouble     ( const AttributeID & attrId ) const = 0;
      
   virtual const ByteString * getByteString ( const AttributeID & attrId ) const = 0;
   virtual const UUID       * getUUID       ( const AttributeID & attrId ) const = 0;
   virtual PInstance          getInstance   ( const AttributeID & attrId ) const = 0;
      
      
   virtual void  setBoolean    ( const AttributeID & attrId, bool     value ) = 0;
   virtual void  setInt32      ( const AttributeID & attrId, int32_t  value ) = 0;
   virtual void  setUInt32     ( const AttributeID & attrId, uint32_t value ) = 0;
       
   virtual void  setInt64      ( const AttributeID & attrId, int64_t  value ) = 0;
   virtual void  setUInt64     ( const AttributeID & attrId, uint64_t value ) = 0;
       
   virtual void  setFloat      ( const AttributeID & attrId, float    value ) = 0;
   virtual void  setDouble     ( const AttributeID & attrId, double   value ) = 0;
     
   virtual void  setByteString ( const AttributeID & attrId, const ByteString  * value ) = 0;
   virtual void  setByteString ( const AttributeID & attrId, const std::string & value ) = 0;
   virtual void  setByteString ( const AttributeID & attrId, const char        * value ) = 0;
   virtual void  setByteString ( const AttributeID & attrId, const uint8_t     * value, std::size_t nBytes ) = 0;
      
   virtual void  setUUID       ( const AttributeID & attrId, const UUID        * value ) = 0;
   
}; // end class Instance

   
   
   //--------------------------------------------------------------------------
   // Array Wrapper Templates
   // 
   
class ArrayWrapperBase
{
  protected:
   PInstance p;
   std::size_t    len;
  public:
   ArrayWrapperBase( const PInstance & _p, std::size_t length ) : p(_p), len(length) {}
   std::size_t length() const { return len; }
      
};
   
template<class T> class ArrayWrapper : public ArrayWrapperBase 
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   T operator[](int i) const { return T(p->getInstance(AttributeID(0,i))); }
   //void set(int i, const T & value ) { p->setInstance(AttributeID(0,i), value); }
};

// ----- Full Template Specializations -----
template<> class ArrayWrapper<bool> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const bool operator[](int i) const { return p->getBoolean(AttributeID(0,i)); }
   void set(int i, bool value ) { p->setBoolean(AttributeID(0,i), value); }
};
template<> class ArrayWrapper<int32_t> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const int32_t operator[](int i) const { return p->getInt32(AttributeID(0,i)); }
   void set(int i, int32_t value ) { p->setInt32(AttributeID(0,i), value); }
};
template<> class ArrayWrapper<uint32_t> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const uint32_t operator[](int i) const { return p->getUInt32(AttributeID(0,i)); }
   void set(int i, uint32_t value ) { p->setUInt32(AttributeID(0,i), value); }
};
template<> class ArrayWrapper<int64_t> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const int64_t operator[](int i) const { return p->getInt64(AttributeID(0,i)); }
   void set(int i, int64_t value ) { p->setInt64(AttributeID(0,i), value); }
};
template<> class ArrayWrapper<uint64_t> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const uint64_t operator[](int i) const { return p->getUInt64(AttributeID(0,i)); }
   void set(int i, uint64_t value ) { p->setUInt64(AttributeID(0,i), value); }
};
template<> class ArrayWrapper<float> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const float operator[](int i) const { return p->getFloat(AttributeID(0,i)); }
   void set(int i, float value ) { p->setFloat(AttributeID(0,i), value); }
};
template<> class ArrayWrapper<double> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const double operator[](int i) const { return p->getDouble(AttributeID(0,i)); }
   void set(int i, double value ) { p->setDouble(AttributeID(0,i), value); }
};
template<> class ArrayWrapper<const ByteString *> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const ByteString * operator[](int i) const { return p->getByteString(AttributeID(0,i)); }
   void set(int i, const ByteString * value) { p->setByteString(AttributeID(0,i), value); }
};
template<> class ArrayWrapper<const UUID *> : public ArrayWrapperBase
{
  public:
   ArrayWrapper(const PInstance & p, std::size_t length) : ArrayWrapperBase(p,length) {}
   const UUID * operator[](int i) const { return p->getUUID(AttributeID(0,i)); }
   void set(int i, const UUID * value ) { p->setUUID(AttributeID(0,i), value); }
};
   
   
   
   
}// end namespace sg

#endif
